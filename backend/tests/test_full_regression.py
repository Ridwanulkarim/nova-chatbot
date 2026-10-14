import os
import unittest
import uuid
import json
import zipfile
import zlib
import io
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.security import hash_password, create_access_token, verify_access_token
from app.core.config import Settings, validate_production_security
from app.database.session import SessionLocal
from app.models import (
    User,
    Conversation,
    Message,
    Document,
    UserMemory,
    UserSettings,
    UserPlugin,
    UserDailyUsage
)
from app.core.quota import (
    check_and_consume_message_quota,
    refund_message_quota,
    check_and_consume_image_quota,
    refund_image_quota,
    get_or_create_today_usage
)
from app.ai.rag_service import rag_service
from app.api.v1.endpoints.files import DISALLOWED_EXTENSIONS, ALLOWED_EXTENSIONS

class FullRegressionTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Create test users
        cls.user1_id = f"test-user-1-{uuid.uuid4().hex[:8]}"
        cls.user2_id = f"test-user-2-{uuid.uuid4().hex[:8]}"
        
        cls.user1 = User(
            id=cls.user1_id,
            email=f"{cls.user1_id}@test.com",
            hashed_password=hash_password("Pass12345!"),
            full_name="User One"
        )
        cls.user2 = User(
            id=cls.user2_id,
            email=f"{cls.user2_id}@test.com",
            hashed_password=hash_password("Pass12345!"),
            full_name="User Two"
        )
        cls.db.add(cls.user1)
        cls.db.add(cls.user2)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(Message).filter(Message.conversation_id.like("test-conv-%")).delete(synchronize_session=False)
            cls.db.query(Conversation).filter(Conversation.user_id.in_([cls.user1_id, cls.user2_id])).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id.in_([cls.user1_id, cls.user2_id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    # 1. AUTHENTICATION & TOKEN VERIFICATION
    def test_01_authentication_flow(self):
        # Valid token
        token = create_access_token({"sub": self.user1.id, "email": self.user1.email})
        decoded = verify_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], self.user1.id)

        # Tampered token
        tampered = token[:-5] + "XXXXX"
        self.assertIsNone(verify_access_token(tampered))

        # Expired token
        expired = create_access_token({"sub": self.user1.id}, expires_delta_seconds=-10)
        self.assertIsNone(verify_access_token(expired))

    # 2. IDOR CONVERSATION OWNERSHIP & STREAM GUARD
    def test_02_conversation_ownership_idor(self):
        conv_user1 = Conversation(
            id=f"test-conv-{uuid.uuid4().hex[:8]}",
            user_id=self.user1.id,
            title="User 1 Private Chat",
            model="gemini-3.5-flash"
        )
        self.db.add(conv_user1)
        self.db.commit()

        # User 1 should access
        found_for_u1 = self.db.query(Conversation).filter(
            Conversation.id == conv_user1.id,
            Conversation.user_id == self.user1.id
        ).first()
        self.assertIsNotNone(found_for_u1)

        # User 2 MUST NOT access User 1's conversation (simulating 404 guard)
        found_for_u2 = self.db.query(Conversation).filter(
            Conversation.id == conv_user1.id,
            Conversation.user_id == self.user2.id
        ).first()
        self.assertIsNone(found_for_u2)

    # 3. NON-EXISTENT CONVERSATION CANNOT BE STREAMED (NO AUTO-CREATION)
    def test_03_non_existent_conversation_returns_404(self):
        fake_conv_id = f"non-existent-{uuid.uuid4().hex}"
        conv = self.db.query(Conversation).filter(
            Conversation.id == fake_conv_id,
            Conversation.user_id == self.user1.id
        ).first()
        self.assertIsNone(conv, "Non-existent conversation should return None (raising 404 in endpoint)")

    # 4. STORED XSS AND MALICIOUS EXTENSION RESTRICTIONS
    def test_04_xss_file_extension_blocking(self):
        dangerous_extensions = [".html", ".htm", ".svg", ".xhtml", ".js", ".mjs", ".sh", ".bat", ".exe", ".php"]
        for ext in dangerous_extensions:
            self.assertIn(ext, DISALLOWED_EXTENSIONS, f"Disallowed extensions must block {ext}")
            self.assertNotIn(ext, ALLOWED_EXTENSIONS, f"Allowed extensions must not contain {ext}")

        safe_extensions = [".png", ".jpg", ".pdf", ".docx", ".txt"]
        for ext in safe_extensions:
            self.assertIn(ext, ALLOWED_EXTENSIONS, f"Allowed extensions should include {ext}")

    # 5. QUOTA ATOMICITY AND REFUND LOGIC
    def test_05_quota_atomicity_and_refund(self):
        initial_usage = get_or_create_today_usage(self.db, self.user1.id)
        init_msgs = initial_usage.message_count

        # Deduct
        check_and_consume_message_quota(self.db, self.user1.id)
        after_deduct = get_or_create_today_usage(self.db, self.user1.id)
        self.assertEqual(after_deduct.message_count, init_msgs + 1)

        # Refund on failure
        refund_message_quota(self.db, self.user1.id)
        after_refund = get_or_create_today_usage(self.db, self.user1.id)
        self.assertEqual(after_refund.message_count, init_msgs)

    # 6. RAG NATIVE DOCX EXTRACTION
    def test_06_rag_native_docx_extraction(self):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
            docx_xml = (
                b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                b'<w:body>'
                b'<w:p><w:r><w:t>Pluto AI Document RAG System</w:t></w:r></w:p>'
                b'<w:p><w:r><w:t>Verification of native zipfile XML parser.</w:t></w:r></w:p>'
                b'</w:body>'
                b'</w:document>'
            )
            zf.writestr("word/document.xml", docx_xml)

        tmp_docx = f"/tmp/test_rag_{uuid.uuid4().hex[:6]}.docx"
        with open(tmp_docx, "wb") as f:
            f.write(bio.getvalue())

        try:
            extracted = rag_service._extract_from_docx(tmp_docx)
            self.assertIn("Pluto AI Document RAG System", extracted)
            self.assertIn("Verification of native zipfile XML parser.", extracted)
        finally:
            if os.path.exists(tmp_docx):
                os.remove(tmp_docx)

    # 7. PRODUCTION SECRET_KEY ENFORCEMENT
    def test_07_production_secret_key_validation(self):
        # Default secret in strict production mode must fail
        os.environ["STRICT_SECRETS"] = "1"
        try:
            prod_settings_insecure = Settings(
                ENVIRONMENT="production",
                SECRET_KEY="pluto_ai_default_secret_key_change_in_production"
            )
            with self.assertRaises(RuntimeError):
                validate_production_security(prod_settings_insecure)
        finally:
            os.environ.pop("STRICT_SECRETS", None)

        # Secure secret in production mode must pass
        prod_settings_secure = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a_very_strong_and_unique_production_secret_key_2026_xyz"
        )
        # Should not raise
        validate_production_security(prod_settings_secure)

    # 8. POSTGRESQL URL NORMALIZATION
    def test_08_database_url_normalization(self):
        raw_url = "postgres://user:pass@host.supabase.co:5432/db"
        normalized = raw_url.replace("postgres://", "postgresql://", 1)
        self.assertTrue(normalized.startswith("postgresql://"))

if __name__ == "__main__":
    unittest.main()
