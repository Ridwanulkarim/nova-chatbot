import os
import uuid
import logging
import urllib.parse
import urllib.request
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ImageGenerationService:
    def __init__(self):
        self.output_dir = settings.UPLOAD_DIR

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "turbo"
    ) -> Dict[str, Any]:
        """
        Generates a high-resolution AI image using Fast Turbo Mode.
        Features zero-failure fallback: if downloading takes more than 10 seconds,
        it instantly returns the direct high-speed Cloudflare CDN URL so the user
        never suffers from read operation timeouts.
        """
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty")

        def _sync_generate():
            os.makedirs(self.output_dir, exist_ok=True)
            filename = f"gen_{uuid.uuid4().hex[:12]}.jpg"
            file_path = os.path.join(self.output_dir, filename)

            # High-speed Pollinations Turbo inference URL
            encoded_prompt = urllib.parse.quote(clean_prompt)
            seed = uuid.uuid4().int % 1000000
            
            # Using model=turbo for lightning-fast generation
            cdn_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true&seed={seed}"

            try:
                req = urllib.request.Request(
                    cdn_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 PlutoAI/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    if data and len(data) > 1000:
                        with open(file_path, "wb") as f:
                            f.write(data)
                        return {
                            "url": f"/uploads/{filename}",
                            "prompt": clean_prompt,
                            "file_path": file_path,
                            "width": width,
                            "height": height,
                            "mode": "turbo"
                        }
            except Exception as dl_err:
                logger.warning(f"Fast Turbo image download skipped or timed out ({dl_err}), falling back to direct Turbo CDN: {cdn_url}")

            # Zero-failure fallback: return direct Turbo CDN URL directly
            return {
                "url": cdn_url,
                "prompt": clean_prompt,
                "file_path": None,
                "width": width,
                "height": height,
                "mode": "turbo_cdn"
            }

        return await asyncio.to_thread(_sync_generate)

image_service = ImageGenerationService()
