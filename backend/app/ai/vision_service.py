import os
from typing import Dict, Any, Optional
try:
    from PIL import Image
except ImportError:
    Image = None

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

        # 3. Create a clean natural summary description
        lines_count = len(result["extracted_text"].splitlines()) if result["extracted_text"] else 0
        desc_parts = [
            f"Image ({result['dimensions']}, {result['format']})"
        ]
        if lines_count > 0:
            desc_parts.append(f"containing {lines_count} lines of recognized text/code")
        else:
            desc_parts.append("no legible text recognized")
        result["description"] = " ".join(desc_parts)

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
            lines.append("Recognized Text, Code, & Screen Elements:")
            lines.append("```text")
            lines.append(extracted)
            lines.append("```")
            lines.append(
                "Use the recognized text, UI labels, code, and contents above to answer the user's inquiry accurately as if you visually inspected the screenshot."
            )
        else:
            lines.append("Note: No legible text was recognized in this image. Describe visual appearance if applicable.")

        lines.append("--- END IMAGE ANALYSIS ---")
        return "\n".join(lines)

vision_service = VisionService()
