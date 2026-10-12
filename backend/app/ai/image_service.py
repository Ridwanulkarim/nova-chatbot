import os
import uuid
import urllib.parse
import urllib.request
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings

class ImageGenerationService:
    def __init__(self):
        self.output_dir = settings.UPLOAD_DIR

    async def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> Dict[str, Any]:
        """Generates a high-resolution AI image and caches it locally."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty")

        def _sync_generate():
            os.makedirs(self.output_dir, exist_ok=True)
            filename = f"gen_{uuid.uuid4().hex[:12]}.jpg"
            file_path = os.path.join(self.output_dir, filename)

            # Generate via Pollinations AI high-speed inference
            encoded_prompt = urllib.parse.quote(clean_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={uuid.uuid4().int % 1000000}"

            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 NovaAI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                with open(file_path, "wb") as f:
                    f.write(data)

            return {
                "url": f"/uploads/{filename}",
                "prompt": clean_prompt,
                "file_path": file_path,
                "width": width,
                "height": height,
            }

        return await asyncio.to_thread(_sync_generate)

image_service = ImageGenerationService()
