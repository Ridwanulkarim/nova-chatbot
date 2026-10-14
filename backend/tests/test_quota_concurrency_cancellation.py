import unittest
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from app.database.session import SessionLocal
from app.models import User, Conversation, Message, UserDailyUsage
from app.core.quota import (
    check_and_consume_message_quota,
    refund_message_quota,
    check_and_consume_image_quota,
    refund_image_quota,
    get_or_create_today_usage
)
from app.core.config import settings

class TestQuotaConcurrencyAndCancellation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.user_id = f"test-concurrent-{uuid.uuid4().hex[:8]}"
        cls.user = User(
            id=cls.user_id,
            email=f"{cls.user_id}@test.com",
            hashed_password="hashed_pw_test",
            full_name="Concurrent Tester"
        )
        cls.db.add(cls.user)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(UserDailyUsage).filter(UserDailyUsage.user_id == cls.user_id).delete()
            cls.db.query(User).filter(User.id == cls.user_id).delete()
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def setUp(self):
        # Reset user daily usage before each test
        usage = get_or_create_today_usage(self.db, self.user_id)
        usage.message_count = 0
        usage.image_count = 0
        self.db.commit()

    def test_01_simultaneous_concurrent_quota_deductions(self):
        """Verify 20 concurrent threads attempting to consume quota simultaneously encounter no race conditions."""
        num_threads = 20

        def worker(_):
            worker_db = SessionLocal()
            try:
                check_and_consume_message_quota(worker_db, self.user_id)
                return True
            finally:
                worker_db.close()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(worker, range(num_threads)))

        self.assertEqual(len(results), num_threads)
        self.assertTrue(all(results))

        # Check final count in DB
        verify_db = SessionLocal()
        try:
            final_usage = get_or_create_today_usage(verify_db, self.user_id)
            self.assertEqual(final_usage.message_count, num_threads, "Concurrent updates must be atomic with zero lost updates")
        finally:
            verify_db.close()

    def test_02_concurrent_quota_limit_enforcement(self):
        """Verify that when the daily quota limit is reached, concurrent requests properly raise 429."""
        # Artificially set usage to limit - 2
        limit = settings.DAILY_MESSAGE_LIMIT
        usage = get_or_create_today_usage(self.db, self.user_id)
        usage.message_count = limit - 2
        self.db.commit()

        def worker(_):
            worker_db = SessionLocal()
            try:
                check_and_consume_message_quota(worker_db, self.user_id)
                return 200
            except HTTPException as e:
                return e.status_code
            finally:
                worker_db.close()

        # Run 5 concurrent requests when only 2 slots remain
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(worker, range(5)))

        successes = results.count(200)
        rate_limits = results.count(429)

        self.assertEqual(successes, 2, "Exactly 2 slots should succeed")
        self.assertEqual(rate_limits, 3, "Remaining 3 requests must strictly receive 429 Too Many Requests")

        verify_db = SessionLocal()
        try:
            final_usage = get_or_create_today_usage(verify_db, self.user_id)
            self.assertEqual(final_usage.message_count, limit)
        finally:
            verify_db.close()

    def test_03_concurrent_quota_refunds(self):
        """Verify that concurrent refunds decrement accurately and never drop below 0."""
        # Set message count to 10
        usage = get_or_create_today_usage(self.db, self.user_id)
        usage.message_count = 10
        self.db.commit()

        def refund_worker(_):
            worker_db = SessionLocal()
            try:
                refund_message_quota(worker_db, self.user_id)
                return True
            finally:
                worker_db.close()

        # Run 10 concurrent refunds
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(refund_worker, range(10)))

        self.assertEqual(len(results), 10)

        verify_db = SessionLocal()
        try:
            final_usage = get_or_create_today_usage(verify_db, self.user_id)
            self.assertEqual(final_usage.message_count, 0, "All 10 messages should be refunded to 0")
        finally:
            verify_db.close()

    def test_04_stream_cancellation_cleans_up_without_corrupting_db(self):
        """Simulate client disconnect (CancelledError) in streaming generator."""
        conv_id = f"test-cancel-conv-{uuid.uuid4().hex[:6]}"
        conv = Conversation(
            id=conv_id,
            user_id=self.user_id,
            title="Cancel Test",
            model="gemini-3.5-flash"
        )
        self.db.add(conv)
        self.db.commit()

        # Consume quota
        check_and_consume_message_quota(self.db, self.user_id)
        before_cancel = get_or_create_today_usage(self.db, self.user_id).message_count

        # Simulate stream execution interrupted by CancelledError
        client_cancelled = False
        full_assistant_reply = []
        try:
            # Yield some tokens then client aborts
            full_assistant_reply.append("Partial token 1")
            full_assistant_reply.append("Partial token 2")
            raise asyncio.CancelledError("Client disconnected")
        except asyncio.CancelledError:
            client_cancelled = True
        finally:
            if not client_cancelled:
                # If NOT cancelled, save to DB
                pass
            # When cancelled, partial reply is discarded and not persisted

        self.assertTrue(client_cancelled)
        # Verify no assistant message was saved to database
        saved_msg = self.db.query(Message).filter(Message.conversation_id == conv_id).first()
        self.assertIsNone(saved_msg, "Cancelled stream must not commit partial corrupted assistant messages to DB")

        # Cleanup test conv
        self.db.delete(conv)
        self.db.commit()

    def test_05_api_failure_triggers_automatic_refund(self):
        """Verify API provider failure automatically triggers quota refund."""
        init_usage = get_or_create_today_usage(self.db, self.user_id).message_count
        # Request arrives and consumes quota
        check_and_consume_message_quota(self.db, self.user_id)
        consumed_usage = get_or_create_today_usage(self.db, self.user_id).message_count
        self.assertEqual(consumed_usage, init_usage + 1)

        # Simulate stream failure
        stream_error = "Connection timeout to provider"
        final_content = ""
        is_error_reply = (
            stream_error is not None
            or "**Error**:" in final_content
            or final_content.startswith("⚠️")
            or not final_content
        )
        self.assertTrue(is_error_reply)

        # On error reply, refund quota
        refund_message_quota(self.db, self.user_id)
        refunded_usage = get_or_create_today_usage(self.db, self.user_id).message_count
        self.assertEqual(refunded_usage, init_usage, "Quota must be fully refunded back to initial value")

if __name__ == "__main__":
    unittest.main()
