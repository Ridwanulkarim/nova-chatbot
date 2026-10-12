import os
import hashlib
from typing import Dict, Any, Optional
try:
    from PIL import Image
except ImportError:
    Image = None

_IMAGE_CACHE: Dict[str, Dict[str, Any]] = {}

class VisionService:
    """
    Multimodal Vision and OCR analysis service for Pluto AI.
    Extracts text, metadata, code, UI labels, and visual characteristics
    from screenshots, photos, and diagrams.
    """

    def analyze_image(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "File not found",
                "extracted_text": "",
                "description": ""
            }

        # Check in-memory cache to avoid redundant OCR calls
        file_hash = None
        try:
            with open(file_path, "rb") as f_hash:
                file_hash = hashlib.md5(f_hash.read()).hexdigest()
            if file_hash in _IMAGE_CACHE:
                return dict(_IMAGE_CACHE[file_hash])
        except Exception:
            pass

        result = {
            "success": True,
            "dimensions": "unknown",
            "format": "unknown",
            "extracted_text": "",
            "description": ""
        }

        # 1. Image metadata via Pillow
        if Image:
            try:
                with Image.open(file_path) as im:
                    width, height = im.size
                    result["dimensions"] = f"{width}x{height}"
                    result["format"] = im.format or "unknown"
                    result["aspect_ratio"] = f"{round(width / max(1, height), 2)}:1"
            except Exception as e:
                result["pillow_error"] = str(e)

        # 2. Native macOS Vision OCR
        try:
            import Vision
            import Cocoa

            input_url = Cocoa.NSURL.fileURLWithPath_(file_path)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
            request.setUsesLanguageCorrection_(True)

            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(input_url, {})
            success, error = handler.performRequests_error_([request], None)

            if success:
                observations = request.results()
                recognized_lines = []
                if observations:
                    for obs in observations:
                        candidates = obs.topCandidates_(1)
                        if candidates:
                            recognized_lines.append(str(candidates[0].string()))
                result["extracted_text"] = "\n".join(recognized_lines).strip()
        except Exception as e:
            result["ocr_error"] = str(e)

        # 3. Universal Cloud OCR Fallback (Runs on Vercel, Linux, or when local OCR is empty)
        if not result["extracted_text"]:
            try:
                import base64
                import io
                import urllib.parse
                import urllib.request
                import json

                # Read and optimize image bytes for OCR
                img_bytes = None
                mime_type = "image/jpeg"
                if Image:
                    try:
                        with Image.open(file_path) as im:
                            rgb_im = im.convert("RGB")
                            rgb_im.thumbnail((1200, 1200))
                            buf = io.BytesIO()
                            rgb_im.save(buf, format="JPEG", quality=80, optimize=True)
                            img_bytes = buf.getvalue()
                    except Exception:
                        img_bytes = None

                if not img_bytes:
                    with open(file_path, "rb") as f_img:
                        img_bytes = f_img.read()
                    mime_type = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"

                api_keys = [
                    os.environ.get("OCR_SPACE_API_KEY", "").strip(),
                    "K82367761188957",
                    "K88726598588957",
                    "K86522521188957",
                    "helloworld"
                ]
                api_keys = [k for k in api_keys if k]

                for key in api_keys:
                    try:
                        import uuid
                        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
                        body_parts = []
                        for param_k, param_v in [
                            ("apikey", key),
                            ("language", "eng"),
                            ("OCREngine", "2"),
                            ("detectOrientation", "true"),
                            ("scale", "true")
                        ]:
                            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{param_k}\"\r\n\r\n{param_v}\r\n".encode("utf-8"))

                        body_parts.append(
                            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"document.jpg\"\r\nContent-Type: {mime_type}\r\n\r\n".encode("utf-8")
                        )
                        body_parts.append(img_bytes)
                        body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
                        post_data = b"".join(body_parts)

                        req = urllib.request.Request(
                            "https://api.ocr.space/parse/image",
                            data=post_data,
                            headers={
                                "Content-Type": f"multipart/form-data; boundary={boundary}",
                                "User-Agent": "PlutoAI/1.0"
                            }
                        )
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            resp_data = json.loads(resp.read().decode("utf-8"))
                            parsed_results = resp_data.get("ParsedResults", [])
                            if parsed_results:
                                cloud_text = parsed_results[0].get("ParsedText", "").strip()
                                if len(cloud_text) > 15:
                                    result["extracted_text"] = cloud_text
                                    break
                    except Exception:
                        continue
            except Exception as cloud_err:
                result["cloud_ocr_error"] = str(cloud_err)

        # 4. Multimodal AI Vision Fallback (Google Gemini Vision)
        if len(result["extracted_text"].strip()) < 30:
            try:
                gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
                if not gemini_key:
                    try:
                        from app.core.config import settings
                        gemini_key = settings.GEMINI_API_KEY or ""
                    except Exception:
                        pass
                if gemini_key:
                    raw_b64 = None
                    try:
                        if Image:
                            with Image.open(file_path) as im_g:
                                rgb_g = im_g.convert("RGB")
                                rgb_g.thumbnail((1000, 1000))
                                buf_g = io.BytesIO()
                                rgb_g.save(buf_g, format="JPEG", quality=75)
                                raw_b64 = base64.b64encode(buf_g.getvalue()).decode("utf-8")
                    except Exception:
                        raw_b64 = None

                    if not raw_b64:
                        with open(file_path, "rb") as f_img:
                            raw_b64 = base64.b64encode(f_img.read()).decode("utf-8")

                    import urllib.request
                    import json
                    for gem_model in ["gemini-3.5-flash", "gemini-2.5-flash"]:
                        try:
                            gem_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gem_model}:generateContent?key={gemini_key}"
                            gem_payload = {
                                "contents": [
                                    {
                                        "parts": [
                                            {"text": "Carefully extract and transcribe all visible questions, problems, text, diagrams, and mathematical expressions from this image verbatim. If this is an exam paper or question sheet, extract every single question number and text in full."},
                                            {"inline_data": {"mime_type": "image/jpeg", "data": raw_b64}}
                                        ]
                                    }
                                ]
                            }
                            gem_req = urllib.request.Request(
                                gem_url,
                                data=json.dumps(gem_payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"}
                            )
                            with urllib.request.urlopen(gem_req, timeout=12) as gem_resp:
                                gem_data = json.loads(gem_resp.read().decode("utf-8"))
                                cands = gem_data.get("candidates", [])
                                if cands:
                                    g_text = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                                    if len(g_text) > 15:
                                        result["extracted_text"] = g_text
                                        break
                        except Exception:
                            continue
            except Exception as g_err:
                result["gemini_ocr_error"] = str(g_err)

        # 5. Create a clean natural summary description
        lines_count = len(result["extracted_text"].splitlines()) if result["extracted_text"] else 0
        desc_parts = [
            f"Image ({result['dimensions']}, {result['format']})"
        ]
        if lines_count > 0:
            desc_parts.append(f"containing {lines_count} lines of recognized text/code")
        else:
            desc_parts.append("visual content analyzed")
        result["description"] = " ".join(desc_parts)

        if file_hash:
            _IMAGE_CACHE[file_hash] = dict(result)

        return result

    def validate_and_optimize(self, data_url: str) -> Dict[str, Any]:
        """
        Validates, decodes, and optimizes base64 image data URLs for multimodal AI models.
        Detects invalid formats, corrupted bytes, and resizes excessively large images.
        """
        import io
        import base64

        if not data_url or not isinstance(data_url, str):
            return {"valid": False, "error": "Missing or empty image data."}
        if not data_url.startswith("data:image"):
            return {"valid": False, "error": "Invalid image format. Expected data URL starting with 'data:image'."}
        try:
            header, b64_str = data_url.split(",", 1)
            mime = header.split(";")[0].replace("data:", "").strip()
            img_bytes = base64.b64decode(b64_str)
        except Exception as e:
            return {"valid": False, "error": f"Failed to decode base64 image data: {str(e)}"}

        if len(img_bytes) == 0:
            return {"valid": False, "error": "Image file is empty (0 bytes)."}

        # Size check: 20MB limit
        if len(img_bytes) > 20 * 1024 * 1024:
            return {"valid": False, "error": "Image exceeds maximum allowed size (20MB)."}

        if not Image:
            return {
                "valid": True,
                "data_url": data_url,
                "mime_type": mime or "image/jpeg",
                "dimensions": "unknown",
                "size_bytes": len(img_bytes),
            }

        try:
            with Image.open(io.BytesIO(img_bytes)) as im:
                im.verify()

            with Image.open(io.BytesIO(img_bytes)) as im:
                w, h = im.size
                # If image is very large (> 2048px or > 4MB), resize & compress to JPEG
                if max(w, h) > 2048 or len(img_bytes) > 4 * 1024 * 1024:
                    im_rgb = im.convert("RGB")
                    im_rgb.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    im_rgb.save(buf, format="JPEG", quality=85, optimize=True)
                    opt_bytes = buf.getvalue()
                    opt_b64 = base64.b64encode(opt_bytes).decode("utf-8")
                    return {
                        "valid": True,
                        "data_url": f"data:image/jpeg;base64,{opt_b64}",
                        "mime_type": "image/jpeg",
                        "dimensions": f"{im_rgb.width}x{im_rgb.height}",
                        "size_bytes": len(opt_bytes),
                    }
                return {
                    "valid": True,
                    "data_url": data_url,
                    "mime_type": mime or "image/jpeg",
                    "dimensions": f"{w}x{h}",
                    "size_bytes": len(img_bytes),
                }
        except Exception as e:
            return {"valid": False, "error": f"Corrupted or unreadable image file: {str(e)}"}

    def format_vision_context(self, filename: str, analysis: Dict[str, Any]) -> str:
        """
        Formats optional OCR transcription without robotic diagnostic error reports.
        OCR failure is completely silent because the model inspects pixels natively.
        """
        extracted = analysis.get("extracted_text", "").strip()
        if extracted and len(extracted) > 15:
            return f"[Auxiliary OCR transcription from {filename}]:\n{extracted}"
        return ""

vision_service = VisionService()
