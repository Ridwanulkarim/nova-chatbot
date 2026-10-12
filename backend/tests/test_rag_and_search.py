import unittest
from app.ai.rag_service import rag_service
from app.ai.search_service import search_service

class TestRAGAndSearch(unittest.TestCase):
    def test_text_chunking(self):
        sample_text = "This is paragraph one about artificial intelligence.\n\n" * 20
        chunks = rag_service.chunk_text(sample_text)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, str)
            self.assertTrue(len(chunk) > 0)

    def test_search_context_formatting(self):
        sample_results = [
            {"title": "FastAPI Docs", "url": "https://fastapi.tiangolo.com", "snippet": "High performance web framework."},
            {"title": "Python Docs", "url": "https://python.org", "snippet": "Python programming language."}
        ]
        context = search_service.format_search_context(sample_results)
        self.assertIn("FastAPI Docs", context)
        self.assertIn("https://fastapi.tiangolo.com", context)
        self.assertIn("BEGIN RETRIEVED REAL-TIME WEB SEARCH RESULTS", context)

    def test_empty_search_formatting(self):
        context = search_service.format_search_context([])
        self.assertEqual(context, "")

if __name__ == "__main__":
    unittest.main()
