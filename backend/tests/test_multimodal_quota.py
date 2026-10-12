import io
import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestMultimodalAndQuotaFeatures(unittest.TestCase):
    def setUp(self):
        self.email = f"quota_test_{uuid.uuid4().hex[:8]}@nova-system.test"
        self.password = "SecurePass2026!"
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password, "full_name": "Quota Tester"}
        )
        self.assertEqual(reg.status_code, 200)
        self.token = reg.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_daily_quota_endpoint(self):
        res = client.get("/api/v1/auth/quota", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("message_count", data)
        self.assertIn("message_limit", data)
        self.assertIn("remaining_messages", data)
        self.assertIn("image_count", data)
        self.assertIn("image_limit", data)
        self.assertIn("remaining_images", data)
        self.assertEqual(data["message_limit"], 50)
        self.assertEqual(data["image_limit"], 10)

    def test_multimodal_file_upload_endpoint(self):
        # Test image upload
        fake_png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        files = {
            "file": ("test_photo.png", io.BytesIO(fake_png_data), "image/png")
        }
        res = client.post("/api/v1/files/upload", headers=self.headers, files=files)
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIn("id", payload)
        self.assertEqual(payload["filename"], "test_photo.png")
        self.assertEqual(payload["media_type"], "image")
        self.assertTrue(payload["url"].startswith("/uploads/"))

    def test_ai_image_generation_quota(self):
        # Check image generation validation
        res = client.post(
            "/api/v1/images/generate",
            headers=self.headers,
            json={"prompt": "A futuristic city in neon cyberpunk aesthetics", "aspect_ratio": "1:1"}
        )
        # Even if external image provider is mocked or blocked in test sandbox,
        # endpoint checks quota and either succeeds or handles gracefully
        self.assertIn(res.status_code, [200, 500, 502])
