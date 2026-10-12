import io
import json
import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.ai.provider_factory import ai_factory
from app.ai.base_provider import BaseAIProvider

class MockTestProvider(BaseAIProvider):
    def list_supported_models(self):
        return [
            {
                "id": "mock-test-model",
                "name": "Mock Test Model",
                "provider": "mock",
                "description": "Mock model for automated unit testing",
                "context_window": 8000,
                "supports_vision": False,
                "supports_streaming": True,
            }
        ]

    async def stream_chat(self, messages, model, temperature=0.7, max_tokens=None):
        for token in ["Hello", " from", " Nova", " AI", " mock!"]:
            yield token

    async def chat(self, messages, model, temperature=0.7, max_tokens=None):
        return "Hello from Nova AI mock!"

client = TestClient(app)

class TestFullSystemWorkflow(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MockTestProvider()
        ai_factory._providers["mock"] = self.mock_provider
        self.email = f"e2e_{uuid.uuid4().hex[:8]}@nova-system.test"
        self.password = "SecurePass2026!"

    def test_complete_user_lifecycle_and_chat(self):
        # 1. Health check
        h_res = client.get("/api/v1/health")
        self.assertEqual(h_res.status_code, 200)
        self.assertEqual(h_res.json()["status"], "online")

        # 2. Register
        reg_res = client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password, "full_name": "E2E Tester"}
        )
        self.assertEqual(reg_res.status_code, 200)
        token = reg_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. Settings update
        set_res = client.patch(
            "/api/v1/settings",
            headers=auth_headers,
            json={"temperature": 0.3, "system_instructions": "Be ultra concise"}
        )
        self.assertEqual(set_res.status_code, 200)
        self.assertEqual(set_res.json()["temperature"], 0.3)

        # 4. User memory management
        mem_res = client.post(
            "/api/v1/settings/memories",
            headers=auth_headers,
            json={"content": "Prefers Python over JavaScript", "category": "preference"}
        )
        self.assertEqual(mem_res.status_code, 200)
        mem_id = mem_res.json()["id"]

        list_mem = client.get("/api/v1/settings/memories", headers=auth_headers)
        self.assertEqual(len(list_mem.json()), 1)

        del_mem = client.delete(f"/api/v1/settings/memories/{mem_id}", headers=auth_headers)
        self.assertEqual(del_mem.status_code, 200)

        # 5. Document upload & RAG chunking
        file_content = b"Nova AI is an intelligent conversational platform with RAG document capabilities.\n\nIt indexes text chunks and supports semantic lookups."
        file_obj = io.BytesIO(file_content)
        upload_res = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": ("architecture_notes.txt", file_obj, "text/plain")}
        )
        self.assertEqual(upload_res.status_code, 200)
        doc_data = upload_res.json()
        doc_id = doc_data["id"]
        self.assertGreater(doc_data["chunk_count"], 0)

        # 6. Create conversation
        conv_res = client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "New Chat", "model": "mock-test-model"}
        )
        self.assertEqual(conv_res.status_code, 200)
        conv_id = conv_res.json()["id"]

        # 7. SSE Streaming response
        stream_res = client.post(
            f"/api/v1/conversations/{conv_id}/messages/stream",
            headers=auth_headers,
            json={"content": "What is Nova AI?", "model": "mock-test-model", "file_ids": [doc_id]}
        )
        self.assertEqual(stream_res.status_code, 200)
        self.assertIn("text/event-stream", stream_res.headers["content-type"])
        body = stream_res.text
        self.assertIn("data:", body)
        self.assertIn("Nova", body)

        # 8. Check persisted messages
        msg_list_res = client.get(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers
        )
        self.assertEqual(msg_list_res.status_code, 200)
        msgs = msg_list_res.json()
        self.assertEqual(len(msgs), 2) # 1 user + 1 assistant
        assistant_msg_id = msgs[1]["id"]

        # 9. Feedback thumbs-up
        fb_res = client.post(
            f"/api/v1/conversations/{assistant_msg_id}/feedback",
            headers=auth_headers,
            json={"feedback": 1}
        )
        self.assertEqual(fb_res.status_code, 200)

        # 10. Clean up document and conversation
        client.delete(f"/api/v1/files/{doc_id}", headers=auth_headers)
        client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers)

if __name__ == "__main__":
    unittest.main()
