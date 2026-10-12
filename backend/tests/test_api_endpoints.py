import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.email = f"user_{uuid.uuid4().hex[:8]}@novachat.test"
        self.password = "StrongPassword123!"

    def test_health_endpoint(self):
        response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["app_name"], "Nova AI")

    def test_register_and_login_flow(self):
        # Register
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password, "full_name": "Nova Tester"}
        )
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        self.assertIn("access_token", reg_data)
        token = reg_data["access_token"]

        # Duplicate register should fail
        dup_resp = client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password}
        )
        self.assertEqual(dup_resp.status_code, 400)

        # Login
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password}
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        # Me endpoint with auth header
        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], self.email)

    def test_conversation_crud_and_isolation(self):
        # User 1
        user1_email = f"user1_{uuid.uuid4().hex[:8]}@novachat.test"
        r1 = client.post("/api/v1/auth/register", json={"email": user1_email, "password": "Password123!"})
        token1 = r1.json()["access_token"]

        # User 2
        user2_email = f"user2_{uuid.uuid4().hex[:8]}@novachat.test"
        r2 = client.post("/api/v1/auth/register", json={"email": user2_email, "password": "Password123!"})
        token2 = r2.json()["access_token"]

        # User 1 creates conversation
        conv_resp = client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token1}"},
            json={"title": "Python Architecture Discussion"}
        )
        self.assertEqual(conv_resp.status_code, 200)
        conv1_id = conv_resp.json()["id"]

        # User 2 CANNOT access User 1's conversation (404 / ownership isolation)
        leak_resp = client.get(
            f"/api/v1/conversations/{conv1_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        self.assertEqual(leak_resp.status_code, 404)

        # User 1 CAN access their conversation
        own_resp = client.get(
            f"/api/v1/conversations/{conv1_id}",
            headers={"Authorization": f"Bearer {token1}"}
        )
        self.assertEqual(own_resp.status_code, 200)
        self.assertEqual(own_resp.json()["title"], "Python Architecture Discussion")

if __name__ == "__main__":
    unittest.main()
