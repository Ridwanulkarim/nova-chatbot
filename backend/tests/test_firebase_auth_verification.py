import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import (
    create_access_token,
    verify_token,
    verify_access_token,
    get_token_algorithm,
    verify_firebase_id_token,
)
from app.database.session import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation

client = TestClient(app)

class TestFirebaseAuthVerification(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_token_algorithm_detection(self):
        # Local HS256 token
        local_tok = create_access_token({"sub": "local_123", "email": "local@test.com"})
        self.assertEqual(get_token_algorithm(local_tok), "HS256")

        # Invalid token
        self.assertIsNone(get_token_algorithm("invalid.token"))
        self.assertIsNone(get_token_algorithm(""))

    def test_legacy_hs256_dual_auth_resolution(self):
        payload = {"sub": f"legacy_{uuid.uuid4().hex[:8]}", "email": "legacy@test.com"}
        token = create_access_token(payload)

        # verify_token should return payload with is_firebase=False
        resolved = verify_token(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["sub"], payload["sub"])
        self.assertEqual(resolved["email"], payload["email"])
        self.assertFalse(resolved["is_firebase"])

        # Tampered HS256 token must fail
        tampered = token[:-4] + "zzzz"
        self.assertIsNone(verify_token(tampered))

    def test_invalid_firebase_token_rejection(self):
        # A malformed or fake RS256 token must return None
        fake_rs256_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.fake_sig"
        self.assertIsNone(verify_firebase_id_token(fake_rs256_token))
        self.assertIsNone(verify_token(fake_rs256_token))

    def test_firebase_token_provisions_user_and_settings(self):
        fb_uid = f"fb_uid_{uuid.uuid4().hex[:12]}"
        fb_email = f"user_{uuid.uuid4().hex[:8]}@firebase.test"
        mock_claims = {
            "uid": fb_uid,
            "sub": fb_uid,
            "email": fb_email,
            "name": "Firebase Explorer",
            "picture": "https://lh3.googleusercontent.com/test_photo.jpg",
            "email_verified": True,
        }

        # Mock verify_firebase_id_token to return valid verified Firebase claims
        with patch("app.core.security.verify_firebase_id_token", return_value=mock_claims):
            fake_fb_token = "eyJhbGciOiJSUzI1NiJ9.eyJ1aWQiOiJ0ZXN0In0.valid_sig"

            # 1. Calling /api/v1/auth/me should auto-provision user
            me_resp = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {fake_fb_token}"}
            )
            self.assertEqual(me_resp.status_code, 200, me_resp.text)
            me_data = me_resp.json()
            self.assertEqual(me_data["id"], fb_uid)
            self.assertEqual(me_data["email"], fb_email)
            self.assertEqual(me_data["full_name"], "Firebase Explorer")

            # 2. Verify database records
            user_in_db = self.db.query(User).filter(User.id == fb_uid).first()
            self.assertIsNotNone(user_in_db)
            self.assertEqual(user_in_db.email, fb_email)
            self.assertEqual(user_in_db.hashed_password, "verified_firebase_session")
            self.assertIsNotNone(user_in_db.settings)

            # 3. Create conversation using Firebase token
            conv_resp = client.post(
                "/api/v1/conversations",
                headers={"Authorization": f"Bearer {fake_fb_token}"},
                json={"title": "Firebase Autonomous Chat"}
            )
            self.assertEqual(conv_resp.status_code, 200, conv_resp.text)
            conv_data = conv_resp.json()
            conv_id = conv_data["id"]

            # Verify conversation is owned by the Firebase user in DB
            conv_in_db = self.db.query(Conversation).filter(Conversation.id == conv_id).first()
            self.assertIsNotNone(conv_in_db)
            self.assertEqual(conv_in_db.user_id, fb_uid)

            # 4. Another user CANNOT access this conversation (Isolation check)
            other_payload = {"sub": f"other_{uuid.uuid4().hex[:8]}", "email": "other@test.com"}
            other_token = create_access_token(other_payload)

            leak_resp = client.get(
                f"/api/v1/conversations/{conv_id}",
                headers={"Authorization": f"Bearer {other_token}"}
            )
            self.assertEqual(leak_resp.status_code, 404)

            # 5. Firebase user CAN access their conversation
            own_resp = client.get(
                f"/api/v1/conversations/{conv_id}",
                headers={"Authorization": f"Bearer {fake_fb_token}"}
            )
            self.assertEqual(own_resp.status_code, 200)
            self.assertEqual(own_resp.json()["title"], "Firebase Autonomous Chat")

if __name__ == "__main__":
    unittest.main()
