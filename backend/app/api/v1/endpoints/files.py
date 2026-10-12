import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentOut
from app.api.deps import get_current_user
from app.core.config import settings
from app.ai.rag_service import rag_service
from app.ai.vision_service import vision_service

router = APIRouter()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".bmp"}
DOC_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".pdf", ".docx", ".yaml", ".yml", ".sh", ".sql", ".ts", ".tsx"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

def detect_media_type(ext: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "document"

@router.get("", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    results = []
    for d in docs:
        ext = os.path.splitext(d.filename)[1].lower()
        rel_url = f"/uploads/{os.path.basename(d.file_path)}"
        results.append({
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "chunk_count": d.chunk_count,
            "url": rel_url,
            "media_type": detect_media_type(ext),
            "created_at": d.created_at
        })
    return results

@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    filename = file.filename or "uploaded_file"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'."
        )

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    # Read and save file safely with size limit
    content_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    media_type = detect_media_type(ext)
    text_chunks = []
    
    # If text document, extract and chunk for RAG
    if media_type == "document":
        extracted_text = rag_service.extract_text_from_file(file_path, file.content_type or "")
        text_chunks = rag_service.chunk_text(extracted_text) if extracted_text else []
    elif media_type == "image":
        # Extract visual characteristics and native macOS Vision OCR
        analysis = vision_service.analyze_image(file_path)
        formatted_context = vision_service.format_vision_context(filename, analysis)
        text_chunks = [formatted_context]
        if analysis.get("extracted_text"):
            ocr_chunks = rag_service.chunk_text(analysis["extracted_text"])
            text_chunks.extend(ocr_chunks)
    elif media_type in ("video", "audio"):
        media_info = f"Uploaded {media_type.capitalize()} Media: {filename} ({len(content_bytes)} bytes, format: {ext.lstrip('.')})."
        text_chunks = [media_info]

    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        file_path=file_path,
        file_size=len(content_bytes),
        mime_type=file.content_type or "application/octet-stream",
        chunk_count=len(text_chunks)
    )
    db.add(doc)
    db.flush()

    # Save chunks
    for idx, chunk_content in enumerate(text_chunks):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_content
        )
        db.add(chunk)

    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "chunk_count": doc.chunk_count,
        "url": f"/uploads/{stored_name}",
        "media_type": media_type,
        "created_at": doc.created_at
    }

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Delete physical file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}
