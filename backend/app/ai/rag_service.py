import os
import re
from typing import List, Dict, Any, Tuple, Optional

from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk

class RAGService:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Splits long text into overlapping chunks based on words/paragraphs."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            words = para.split()
            word_count = len(words)

            if current_length + word_count <= self.chunk_size:
                current_chunk.append(para)
                current_length += word_count
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                # If paragraph itself is larger than chunk_size, split into sub-chunks
                if word_count > self.chunk_size:
                    for i in range(0, word_count, self.chunk_size - self.chunk_overlap):
                        sub_chunk = " ".join(words[i:i + self.chunk_size])
                        chunks.append(sub_chunk)
                    current_chunk = []
                    current_length = 0
                else:
                    current_chunk = [para]
                    current_length = word_count

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [text[:2000]]

    def _extract_from_docx(self, file_path: str) -> str:
        """Extracts text from DOCX using python-docx or pure zipfile standard library."""
        try:
            import docx
            doc = docx.Document(file_path)
            lines = [p.text for p in doc.paragraphs if p.text.strip()]
            if lines:
                return "\n\n".join(lines)
        except Exception:
            pass

        # Native fallback: extract word/document.xml from docx zip archive
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path, "r") as zf:
                if "word/document.xml" not in zf.namelist():
                    return ""
                xml_data = zf.read("word/document.xml")
                tree = ET.fromstring(xml_data)
                texts = []
                for elem in tree.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        texts.append(elem.text)
                    elif elem.tag.endswith("}p"):
                        texts.append("\n")
                return "".join(texts).strip()
        except Exception:
            return ""

    def _extract_from_pdf(self, file_path: str) -> str:
        """Extracts text from PDF using pypdf if available, or native zlib PDF stream reader."""
        # 1. Try pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for p in reader.pages:
                t = p.extract_text()
                if t and t.strip():
                    pages_text.append(t.strip())
            if pages_text:
                return "\n\n".join(pages_text)
        except Exception:
            pass

        # 2. Native PDF stream extractor using zlib
        try:
            import zlib
            extracted_text = []
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            stream_matches = re.findall(b"stream[\r\n]+(.*?)[\r\n]+endstream", pdf_bytes, re.DOTALL)
            for s in stream_matches:
                data = s
                try:
                    data = zlib.decompress(s)
                except Exception:
                    pass

                # Extract (text) Tj
                tj_matches = re.findall(rb"\((.*?)\)\s*Tj", data)
                for m in tj_matches:
                    try:
                        decoded = m.decode("latin1", errors="ignore")
                        if decoded.strip():
                            extracted_text.append(decoded)
                    except Exception:
                        pass

                # Extract [(text)] TJ
                array_matches = re.findall(rb"\[(.*?)\]\s*TJ", data)
                for arr in array_matches:
                    parts = re.findall(rb"\((.*?)\)", arr)
                    for part in parts:
                        try:
                            decoded = part.decode("latin1", errors="ignore")
                            if decoded.strip():
                                extracted_text.append(decoded)
                        except Exception:
                            pass

            return " ".join(extracted_text).strip()
        except Exception:
            return ""

    def extract_text_from_file(self, file_path: str, mime_type: str = "") -> str:
        """Extracts text content safely from uploaded files respecting file types."""
        if not os.path.exists(file_path):
            return ""

        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. PDF
        if ext == ".pdf" or "pdf" in mime_type.lower():
            pdf_text = self._extract_from_pdf(file_path)
            if pdf_text:
                return pdf_text

        # 2. DOCX
        if ext == ".docx" or "word" in mime_type.lower() or "officedocument" in mime_type.lower():
            docx_text = self._extract_from_docx(file_path)
            if docx_text:
                return docx_text

        # 3. Text, Markdown, CSV, JSON, Code files
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def search_relevant_chunks(
        self,
        db: Session,
        user_id: str,
        query: str,
        file_ids: Optional[List[str]] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Retrieves and scores chunks relevant to the user query."""
        if not query.strip():
            return []

        # Tokenize query words
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []

        # Query chunks belonging to user's documents
        base_query = db.query(DocumentChunk, Document.filename)\
            .join(Document, DocumentChunk.document_id == Document.id)\
            .filter(Document.user_id == user_id)

        if file_ids:
            base_query = base_query.filter(Document.id.in_(file_ids))

        all_chunks = base_query.all()
        scored_chunks: List[Tuple[float, DocumentChunk, str]] = []

        for chunk, filename in all_chunks:
            chunk_words = re.findall(r"\w+", chunk.content.lower())
            if not chunk_words:
                continue
            
            # Simple TF keyword scoring
            matches = sum(1 for w in chunk_words if w in query_words)
            if matches > 0:
                score = matches / (len(chunk_words) ** 0.5)
                scored_chunks.append((score, chunk, filename))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_chunks[:top_k]

        return [
            {
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number
            }
            for _, chunk, filename in top_results
        ]

    def format_rag_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Formats document context for grounding responses."""
        if not retrieved_chunks:
            return ""

        context_lines = [
            "\n--- BEGIN RETRIEVED USER DOCUMENT CONTEXT (RAG) ---",
            "CRITICAL INSTRUCTION: The following excerpts are extracted from user uploaded documents. Ground your answer in these facts. If the document excerpts do not provide enough information to answer the question, clearly state that the provided documents do not contain sufficient details.",
        ]

        for idx, chunk in enumerate(retrieved_chunks, 1):
            source_info = f"Document: {chunk['filename']} (Section {chunk['chunk_index'] + 1})"
            if chunk.get("page_number"):
                source_info += f", Page {chunk['page_number']}"
            context_lines.append(f"[{idx}] {source_info}\nExcerpt:\n{chunk['content']}\n")

        context_lines.append("--- END RETRIEVED USER DOCUMENT CONTEXT ---\n")
        return "\n".join(context_lines)

rag_service = RAGService()
