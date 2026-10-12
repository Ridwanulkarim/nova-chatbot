import re
from typing import Dict, Any, List, Optional
from app.ai.math_service import math_service
from app.ai.search_service import search_service
from app.ai.rag_service import rag_service
from app.ai.vision_service import vision_service
from app.ai.image_service import image_service

class ToolOrchestrator:
    """
    Intelligent Tool Routing Engine for Nova AI.
    Analyzes intent, input modalities, and routes requests to:
    - Symbolic Math Solver (SymPy)
    - Multimodal Vision & OCR (Apple Vision)
    - Web Grounding & Live Search (DuckDuckGo)
    - Document RAG Engine
    - Photorealistic Image Studio (Flux / SDXL)
    """

    def analyze_intent(
        self,
        query: str,
        has_attachments: bool = False,
        web_search_forced: bool = False
    ) -> Dict[str, Any]:
        clean = query.strip().lower()

        # 1. Image Generation Intent
        is_image_gen = (
            clean.startswith(("/image", "generate an image", "create an image", "draw an image", "make an image", "draw a picture"))
            or "generate an image of" in clean
            or "create an image of" in clean
            or "generate a picture of" in clean
        )
        if is_image_gen:
            prompt = query
            for pfx in ["/image", "generate an image of", "generate an image", "create an image of", "create an image", "draw an image of", "make an image of"]:
                if clean.startswith(pfx):
                    prompt = query[len(pfx):].strip(" :,-")
                    break
            return {
                "route": "IMAGE_GENERATION",
                "image_prompt": prompt or query
            }

        # 2. Mathematical Intent
        if math_service.is_math_query(query):
            math_solution = math_service.solve_expression(query)
            if math_solution.get("success"):
                return {
                    "route": "MATH_SOLVER",
                    "solution": math_solution
                }

        # 3. Vision / Screenshot Intent
        if has_attachments or "screenshot" in clean or "in this image" in clean or "in this photo" in clean:
            return {
                "route": "VISION_MULTIMODAL"
            }

        # 4. Web Search Intent
        time_sensitive_keywords = ["latest", "recent", "today", "news", "current price", "who won", "2026", "who is the current"]
        needs_search = web_search_forced or any(kw in clean for kw in time_sensitive_keywords)
        if needs_search:
            return {
                "route": "WEB_SEARCH"
            }

        # 5. Default General Reasoning
        return {
            "route": "GENERAL_CHAT"
        }

tool_orchestrator = ToolOrchestrator()
