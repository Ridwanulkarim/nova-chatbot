import unittest
import urllib.request
import json
import uuid
import base64
import os
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def get_real_firebase_user_and_token():
    api_key = 'AIzaSyB9IZTtx3sNbGNMmQZuHX9_xy5fBWL_BJI'
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}'
    test_email = f'user_a_{uuid.uuid4().hex[:6]}@plutotest.local'
    test_pw = 'PlutoPass2026!'

    data = json.dumps({
        'email': test_email,
        'password': test_pw,
        'returnSecureToken': True
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode('utf-8'))
        return res.get('localId'), res.get('email'), res.get('idToken')

class TestStep10EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Obtain real Firebase ID token for User A
        cls.user_a_uid, cls.user_a_email, cls.user_a_token = get_real_firebase_user_and_token()
        cls.auth_header_a = {"Authorization": f"Bearer {cls.user_a_token}"}

        # 2. Obtain real Firebase ID token for User B
        cls.user_b_uid, cls.user_b_email, cls.user_b_token = get_real_firebase_user_and_token()
        cls.auth_header_b = {"Authorization": f"Bearer {cls.user_b_token}"}

    def test_item5_auth_me_with_real_firebase_token(self):
        """Item 5: /api/v1/auth/me accepts real Firebase ID token and returns authenticated user."""
        resp = client.get("/api/v1/auth/me", headers=self.auth_header_a)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["id"], self.user_a_uid)
        self.assertEqual(data["email"], self.user_a_email)
        self.assertTrue(data["is_active"])

    def test_item6_rejection_of_invalid_tokens(self):
        """Item 6: Verify missing, expired, malformed, and invalid tokens are rejected."""
        # 1. Missing Authorization header
        r1 = client.get("/api/v1/auth/me")
        self.assertEqual(r1.status_code, 401)
        self.assertIn("Not authenticated", r1.text)

        # 2. Malformed token
        r2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed.token.value"})
        self.assertEqual(r2.status_code, 401)

        # 3. Non-bearer format
        r3 = client.get("/api/v1/auth/me", headers={"Authorization": "Basic 12345"})
        self.assertEqual(r3.status_code, 401)

        # 4. Tampered Firebase ID token (modified signature)
        tampered_fb = self.user_a_token[:-8] + "ABCDEFGH"
        r4 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_fb}"})
        self.assertEqual(r4.status_code, 401)

        # 5. Expired legacy token
        expired_token = create_access_token({"sub": "expired_user"}, expires_delta_seconds=-60)
        r5 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(r5.status_code, 401)

    def test_item7_conversation_isolation_between_users(self):
        """Item 7: User A creates a conversation; User B cannot read, modify, or delete it."""
        # User A creates conversation
        create_resp = client.post(
            "/api/v1/conversations",
            headers=self.auth_header_a,
            json={"title": "Confidential Research by User A"}
        )
        self.assertEqual(create_resp.status_code, 200, create_resp.text)
        conv_id = create_resp.json()["id"]

        # User B attempts to read User A's conversation -> MUST return 404
        read_resp = client.get(f"/api/v1/conversations/{conv_id}", headers=self.auth_header_b)
        self.assertEqual(read_resp.status_code, 404, "User B was able to read User A's conversation!")

        # User B attempts to update User A's conversation -> MUST return 404
        update_resp = client.patch(
            f"/api/v1/conversations/{conv_id}",
            headers=self.auth_header_b,
            json={"title": "Hacked Title by User B"}
        )
        self.assertEqual(update_resp.status_code, 404, "User B was able to modify User A's conversation!")

        # User B attempts to delete User A's conversation -> MUST return 404
        del_resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=self.auth_header_b)
        self.assertEqual(del_resp.status_code, 404, "User B was able to delete User A's conversation!")

        # User A CAN read their own conversation
        own_read = client.get(f"/api/v1/conversations/{conv_id}", headers=self.auth_header_a)
        self.assertEqual(own_read.status_code, 200)
        self.assertEqual(own_read.json()["title"], "Confidential Research by User A")

        # User A CAN delete their own conversation
        own_del = client.delete(f"/api/v1/conversations/{conv_id}", headers=self.auth_header_a)
        self.assertEqual(own_del.status_code, 200)

    def test_item8_history_streaming_and_upload(self):
        """Item 8: Verify conversation history, message streaming, and image upload for authenticated user."""
        # 1. Test image upload
        img_buffer = BytesIO()
        test_img = Image.new("RGB", (64, 64), color="purple")
        test_img.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        files = {"file": ("test_avatar.png", img_bytes, "image/png")}
        upload_resp = client.post("/api/v1/files/upload", headers=self.auth_header_a, files=files)
        self.assertEqual(upload_resp.status_code, 200, upload_resp.text)
        upload_data = upload_resp.json()
        doc_id = upload_data["id"]
        doc_url = upload_data["url"]
        self.assertIn(".png", upload_data["filename"])

        # 2. Test conversation creation and message streaming
        conv_resp = client.post(
            "/api/v1/conversations",
            headers=self.auth_header_a,
            json={"title": "Streaming Test Conversation"}
        )
        self.assertEqual(conv_resp.status_code, 200)
        conv_id = conv_resp.json()["id"]

        # Stream a harmless test prompt with the uploaded attachment
        stream_payload = {
            "content": "Hello Pluto, please calculate 2+2.",
            "model": "openai/gpt-oss-120b",
            "attachments": [{
                "filename": "test_avatar.png",
                "media_type": "image",
                "url": doc_url
            }]
        }

        stream_resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages/stream",
            headers=self.auth_header_a,
            json=stream_payload
        )
        self.assertEqual(stream_resp.status_code, 200, stream_resp.text)
        self.assertIn("text/event-stream", stream_resp.headers.get("content-type", ""))

        # 3. Verify conversation history has user message saved
        hist_resp = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=self.auth_header_a)
        self.assertEqual(hist_resp.status_code, 200)
        messages = hist_resp.json()
        self.assertTrue(len(messages) >= 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("2+2", messages[0]["content"])

        # 4. Clean up test document
        del_doc_resp = client.delete(f"/api/v1/files/{doc_id}", headers=self.auth_header_a)
        self.assertEqual(del_doc_resp.status_code, 200)

if __name__ == "__main__":
    unittest.main()
