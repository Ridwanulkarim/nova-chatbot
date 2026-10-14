import os
import uuid
import logging
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger("pluto.storage")

class StorageService:
    def __init__(self):
        self.backend = getattr(settings, "STORAGE_BACKEND", "local")

    def save_file(self, content_bytes: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        """
        Save file content to configured storage backend.
        Returns:
            Tuple of (file_path_or_key, public_or_local_url)
        """
        stored_name = f"{uuid.uuid4().hex}_{filename}"

        if self.backend == "s3" and settings.S3_BUCKET_NAME:
            try:
                import boto3
                session_kwargs = {
                    "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
                    "region_name": settings.S3_REGION_NAME or "us-east-1",
                }
                if settings.S3_ENDPOINT_URL:
                    session_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

                s3_client = boto3.client("s3", **session_kwargs)
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type

                s3_key = f"uploads/{stored_name}"
                s3_client.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=content_bytes,
                    **extra_args
                )
                url = f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                if settings.S3_ENDPOINT_URL:
                    url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}"
                return s3_key, url
            except Exception as e:
                logger.error(f"S3 upload failed, falling back to local filesystem: {e}")

        # Local storage fallback (or default)
        upload_dir = settings.UPLOAD_DIR
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except Exception:
            pass

        file_path = os.path.join(upload_dir, stored_name)
        try:
            with open(file_path, "wb") as f:
                f.write(content_bytes)
        except OSError:
            import tempfile
            file_path = os.path.join(tempfile.gettempdir(), stored_name)
            with open(file_path, "wb") as f:
                f.write(content_bytes)

        rel_url = f"/uploads/{stored_name}"
        return file_path, rel_url

storage_service = StorageService()
