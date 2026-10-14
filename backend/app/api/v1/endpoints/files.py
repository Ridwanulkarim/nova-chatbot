import os
import re
import shutil
import uuid
import base64
import tempfile
from datetime import datetime, timezone
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

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif", ".tiff", ".tif", ".jfif", ".ico", ".avif"}
DOC_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".pdf", ".docx", ".yaml", ".yml", ".sql"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
DISALLOWED_EXTENSIONS = {".html", ".htm", ".svg", ".xhtml", ".js", ".mjs", ".sh", ".bat", ".exe", ".php"}
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
    raw_filename = file.filename or "uploaded_file"
    # Sanitize filename against directory traversal and null-byte injection
    clean_filename = os.path.basename(raw_filename).replace("\x00", "").strip()
    clean_filename = re.sub(r'[/\\:\0]', '_', clean_filename)
    if not clean_filename or clean_filename in [".", ".."]:
        clean_filename = "uploaded_file"

    ext = os.path.splitext(clean_filename)[1].lower()
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HTML, SVG, and executable script uploads are restricted for security reasons."
        )

    if ext not in ALLOWED_EXTENSIONS:
        # If no extension or unknown image type, check content_type
        if file.content_type and file.content_type.startswith("image/"):
            ext = ".png"
            clean_filename = f"{clean_filename}.png"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'."
            )

    # Ensure upload directory exists safely
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    except Exception:
        pass

    stored_name = f"{uuid.uuid4().hex}_{clean_filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    # Read content bytes
    content_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Write file safely; fallback to temp directory if primary directory is not writable
    write_succeeded = False
    try:
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        write_succeeded = True
    except OSError:
        file_path = os.path.join(tempfile.gettempdir(), stored_name)
        try:
            with open(file_path, "wb") as f:
                f.write(content_bytes)
            write_succeeded = True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded file: {str(e)}"
            )

    if not write_succeeded or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file on server."
        )

    media_type = detect_media_type(ext)
    
    # Generate URL: for images, embed optimized base64 data URL so preview & native vision always work on Vercel
    image_url = f"/uploads/{stored_name}"
    if media_type == "image":
        try:
            b64 = base64.b64encode(content_bytes).decode("utf-8")
            mime = file.content_type or f"image/{ext.lstrip('.')}"
            raw_data_url = f"data:{mime};base64,{b64}"
            opt = vision_service.validate_and_optimize(raw_data_url)
            image_url = opt["data_url"] if opt.get("valid") and opt.get("data_url") else raw_data_url
        except Exception:
            pass

    text_chunks = []
    
    # Only index text documents (PDF, TXT, DOCX, etc.) into RAG chunks — images use direct multimodal vision
    if media_type == "document":
        try:
            extracted_text = rag_service.extract_text_from_file(file_path, file.content_type or "")
            text_chunks = rag_service.chunk_text(extracted_text) if extracted_text else []
        except Exception:
            text_chunks = []

    doc_id = str(uuid.uuid4())
    # Save document record in DB for all uploads so it can be managed, referenced, and deleted
    created_at = datetime.now(timezone.utc)
    try:
        doc = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=clean_filename,
            file_path=file_path,
            file_size=len(content_bytes),
            mime_type=file.content_type or "application/octet-stream",
            chunk_count=len(text_chunks),
            created_at=created_at
        )
        db.add(doc)
        db.flush()

        for idx, chunk_content in enumerate(text_chunks):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_content
            )
            db.add(chunk)

        db.commit()
        db.refresh(doc)
        created_at = doc.created_at
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while registering uploaded file: {str(e)}"
        )

    return {
        "id": doc_id,
        "filename": clean_filename,
        "file_size": len(content_bytes),
        "mime_type": file.content_type or "application/octet-stream",
        "chunk_count": len(text_chunks),
        "url": f"/uploads/{stored_name}",
        "data_url": image_url if image_url.startswith("data:") else None,
        "media_type": media_type,
        "extracted_text": None,
        "created_at": created_at
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
