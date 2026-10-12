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

                # If Pillow is available, compress to optimized JPEG to stay well under cloud OCR payload limits (< 1MB)
                raw_b64 = None
                img_fmt = "jpeg"
                if Image:
                    try:
                        with Image.open(file_path) as im:
                            buf = io.BytesIO()
                            rgb_im = im.convert("RGB")
                            # Resize if oversized (max dimension 1800px)
                            max_dim = max(rgb_im.size)
                            if max_dim > 1800:
                                scale = 1800.0 / max_dim
                                new_size = (int(rgb_im.size[0] * scale), int(rgb_im.size[1] * scale))
                                rgb_im = rgb_im.resize(new_size, Image.Resampling.LANCZOS)
                            rgb_im.save(buf, format="JPEG", quality=85, optimize=True)
                            raw_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    except Exception:
                        raw_b64 = None

                if not raw_b64:
                    with open(file_path, "rb") as f_img:
                        raw_b64 = base64.b64encode(f_img.read()).decode("utf-8")
                    img_fmt = result.get("format", "png").lower()
                    if img_fmt not in ["jpeg", "jpg", "png", "webp", "gif"]:
                        img_fmt = "png"

                api_key = os.environ.get("OCR_SPACE_API_KEY", "helloworld")
                data = urllib.parse.urlencode({
                    "base64Image": f"data:image/{img_fmt};base64,{raw_b64}",
                    "apikey": api_key,
                    "language": "eng",
                    "detectOrientation": "true",
                    "isTable": "true",
                    "scale": "true"
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.ocr.space/parse/image",
                    data=data,
                    headers={"User-Agent": "PlutoAI/1.0"}
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    parsed_results = resp_data.get("ParsedResults", [])
                    if parsed_results:
                        cloud_text = parsed_results[0].get("ParsedText", "").strip()
                        if cloud_text:
                            result["extracted_text"] = cloud_text
            except Exception as cloud_err:
                result["cloud_ocr_error"] = str(cloud_err)

        # 4. Create a clean natural summary description
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

    def format_vision_context(self, filename: str, analysis: Dict[str, Any]) -> str:
        extracted = analysis.get("extracted_text", "").strip()
        dim = analysis.get("dimensions", "unknown")
        fmt = analysis.get("format", "unknown")

        lines = [
            f"--- ATTACHED SCREENSHOT / IMAGE ANALYSIS: {filename} ---",
            f"Image Resolution: {dim} ({fmt})",
        ]

        if extracted:
            lines.append("Recognized Text, Questions, Code & Mathematical Contents from Image:")
            lines.append("```text")
            lines.append(extracted)
            lines.append("```")
            lines.append(
                "CRITICAL INSTRUCTION: The user has uploaded an image containing text/questions (e.g. an exam question paper, code, or document). "
                "Carefully read all the recognized questions and text above, and provide complete, detailed, step-by-step answers "
                "to what the user is asking about the image. Do NOT say you cannot see the image; use the exact extracted text above!"
            )
        else:
            lines.append("Note: Visual content detected. Assist the user with their inquiry.")

        lines.append("--- END IMAGE ANALYSIS ---")
        return "\n".join(lines)

vision_service = VisionService()
