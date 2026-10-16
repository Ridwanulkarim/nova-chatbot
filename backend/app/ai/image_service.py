import os
import re
import uuid
import logging
import urllib.parse
import urllib.request
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

IMAGE_PREFIXES = [
    "generate an image of", "generate a image of", "generate image of", "generate an image", "generate a image", "generate image",
    "generate a picture of", "generate an picture of", "generate picture of", "generate a picture", "generate picture",
    "generate a photo of", "generate photo of", "generate a photo", "generate photo",
    "create an image of", "create a image of", "create image of", "create an image", "create a image", "create image",
    "create a picture of", "create picture of", "create a picture", "create picture",
    "create a photo of", "create photo of", "create a photo", "create photo",
    "draw an image of", "draw a image of", "draw image of", "draw an image", "draw a image", "draw image",
    "draw a picture of", "draw picture of", "draw a picture", "draw picture",
    "draw a ", "draw an ", "draw me a ", "draw me an ", "draw me ", "draw ",
    "paint a picture of", "paint an image of", "paint a ", "paint an ", "paint ",
    "make an image of", "make a image of", "make image of", "make an image", "make a image", "make image",
    "make a picture of", "make picture of", "make a picture", "make picture",
    "make a photo of", "make photo of",
    "image of a ", "image of an ", "image of ",
    "picture of a ", "picture of an ", "picture of ",
    "photo of a ", "photo of an ", "photo of ",
    "ai image of ", "ai picture of ", "ai photo of ",
]

IMAGE_KW_REGEX = re.compile(
    r'\b(?:can you\s+|could you\s+|please\s+)?(?:generate|create|draw|make|render)\s+(?:an?\s+|the\s+)?(?:image|picture|photo|illustration|drawing)\s+of\s+(.+)',
    re.IGNORECASE
)

BANGLA_IMAGE_REGEX = re.compile(
    r'(.+?)\s*(?:-?er\s+)?(?:ekta\s+)?(?:chobi|chobi banao|chobi toiri koro|chobi eke dao|chobi dekhao|ছবি|ছবি বানাও|ছবি তৈরি করো|ছবি এঁকে দাও)',
    re.IGNORECASE
)

def detect_image_request(text: str) -> Tuple[bool, str]:
    """
    Detects if a user message is requesting AI image generation.
    Supports /image, all natural variations ('generate a image', 'generate an image',
    'draw a', 'create photo of', etc.), conversational queries, and Bangla requests.
    Returns (is_image_request, cleaned_prompt).
    """
    if not text or not isinstance(text, str):
        return False, ""
    raw = text.strip()
    clean_low = raw.lower()

    if clean_low.startswith("/image"):
        extracted = raw[6:].strip(" :,-")
        return True, extracted or raw

    for pfx in sorted(IMAGE_PREFIXES, key=len, reverse=True):
        if clean_low.startswith(pfx):
            prompt = raw[len(pfx):].strip(" :,-")
            return True, prompt or raw

    m = IMAGE_KW_REGEX.search(raw)
    if m:
        return True, m.group(1).strip(" :,-?.!")

    if any(k in clean_low for k in ["chobi banao", "chobi toiri koro", "chobi eke dao", "chobi dekhao", "ছবি বানাও", "ছবি তৈরি করো", "ছবি এঁকে দাও"]):
        bm = BANGLA_IMAGE_REGEX.search(raw)
        prompt = bm.group(1).strip(" :,-") if bm else raw
        return True, prompt or raw

    return False, ""

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
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = resp.read()
                    if data and len(data) > 1000:
                        # Auto-remove bottom watermark using Pillow
                        clean_bytes = data
                        try:
                            import io
                            from PIL import Image
                            with Image.open(io.BytesIO(data)) as raw_img:
                                w, h = raw_img.size
                                crop_h = max(28, int(h * 0.055))
                                cropped = raw_img.crop((0, 0, w, h - crop_h))
                                clean_img = cropped.resize((w, h), Image.Resampling.LANCZOS)
                                out_buf = io.BytesIO()
                                clean_img.save(out_buf, format="JPEG", quality=95)
                                clean_bytes = out_buf.getvalue()
                        except Exception as crop_err:
                            logger.warning(f"Watermark auto-crop skipped: {crop_err}")

                        # Save clean image to local upload storage
                        try:
                            with open(file_path, "wb") as f:
                                f.write(clean_bytes)
                        except Exception:
                            pass

                        # Encode clean image as base64 data URL for zero-watermark, zero-404 rendering
                        import base64
                        b64_str = base64.b64encode(clean_bytes).decode("utf-8")
                        clean_data_url = f"data:image/jpeg;base64,{b64_str}"

                        return {
                            "url": clean_data_url,
                            "download_url": f"/uploads/{filename}",
                            "prompt": clean_prompt,
                            "file_path": file_path,
                            "width": width,
                            "height": height,
                            "mode": "clean_turbo"
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
