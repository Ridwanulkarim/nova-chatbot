import json
import urllib.request
import urllib.error
import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.ai.base_provider import BaseAIProvider

logger = logging.getLogger("pluto.ai.gemini")

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "gemini-3.5-flash",
                "name": "Gemini 3.5 Flash (Google)",
                "provider": "gemini",
                "description": "Flagship fast multimodal model with native pixel-level vision and reasoning",
                "context_window": 1048576,
                "supports_vision": True,
                "supports_streaming": True,
            },
            {
                "id": "gemini-3.8-flash",
                "name": "Gemini 3.8 Flash (Google)",
                "provider": "gemini",
                "description": "Next-generation multimodal reasoning and visual understanding",
                "context_window": 1048576,
                "supports_vision": True,
                "supports_streaming": True,
            }
        ]

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        system_instructions = []
        contents = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")

            if role == "system":
                if isinstance(content, str):
                    system_instructions.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            system_instructions.append(item.get("text", ""))
                        elif isinstance(item, str):
                            system_instructions.append(item)
                continue

            # Assistant role
            if role == "assistant":
                text_val = content if isinstance(content, str) else str(content)
                contents.append({
                    "role": "model",
                    "parts": [{"text": text_val}]
                })
                continue

            # User role: handle string or multimodal parts list
            parts: List[Dict[str, Any]] = []

            if isinstance(content, str):
                if content.strip():
                    parts.append({"text": content})
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, str):
                        if item.strip():
                            parts.append({"text": item})
                    elif isinstance(item, dict):
                        item_type = item.get("type", "")
                        if item_type == "text":
                            text_body = item.get("text", "")
                            if text_body:
                                parts.append({"text": text_body})
                        elif item_type == "image_url":
                            image_info = item.get("image_url", {})
                            url_val = image_info.get("url") if isinstance(image_info, dict) else str(image_info)
                            if url_val and url_val.startswith("data:image"):
                                try:
                                    header, b64_clean = url_val.split(",", 1)
                                    mime = header.split(";")[0].replace("data:", "").strip()
                                    if not mime or not mime.startswith("image/"):
                                        mime = "image/jpeg"
                                    parts.append({
                                        "inline_data": {
                                            "mime_type": mime,
                                            "data": b64_clean.strip()
                                        }
                                    })
                                    logger.info(
                                        f"Processed multimodal image part for Gemini: MIME={mime}, base64_len={len(b64_clean)}"
                                    )
                                except Exception as parse_err:
                                    logger.warning(f"Failed parsing image data URL for Gemini: {parse_err}")
                            elif url_val:
                                parts.append({"text": f"[Referenced Image URL: {url_val}]"})

            # Also check if explicit images list was passed
            if "images" in m and isinstance(m["images"], list):
                for img in m["images"]:
                    img_data = img.get("data") or img.get("data_url") or ""
                    mime = img.get("mime_type") or "image/jpeg"
                    if img_data.startswith("data:"):
                        header, img_data = img_data.split(",", 1)
                        mime = header.split(";")[0].replace("data:", "").strip() or mime
                    if img_data:
                        parts.append({
                            "inline_data": {
                                "mime_type": mime,
                                "data": img_data.strip()
                            }
                        })

            if not parts:
                parts = [{"text": "Please analyze the provided request."}]

            contents.append({
                "role": "user",
                "parts": parts
            })

        payload: Dict[str, Any] = {"contents": contents}

        if system_instructions:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_instructions)}]
            }

        return payload

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        clean_model = model.replace("google/", "").replace("models/", "").strip()
        # Map legacy or deprecated model IDs to modern active ones
        model_aliases = {
            "gemini-2.5-flash": "gemini-3.5-flash",
            "gemini-2.0-flash": "gemini-3.5-flash",
            "gemini-1.5-flash": "gemini-3.5-flash",
            "gemini-1.5-pro": "gemini-3.5-flash",
            "gemini-pro": "gemini-3.5-flash",
            "gemini-flash": "gemini-3.5-flash",
        }
        clean_model = model_aliases.get(clean_model, clean_model)
        if not clean_model:
            clean_model = "gemini-3.5-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._convert_messages(messages)

        # Build diagnostic log summary (without leaking API keys or full base64 strings)
        img_count = 0
        text_char_count = 0
        for c in payload.get("contents", []):
            for p in c.get("parts", []):
                if "inline_data" in p:
                    img_count += 1
                if "text" in p:
                    text_char_count += len(p["text"])
        logger.info(
            f"Dispatching Gemini request: model={clean_model}, messages={len(payload.get('contents', []))}, "
            f"images={img_count}, text_chars={text_char_count}"
        )

        gen_config: Dict[str, Any] = {}
        if temperature is not None:
            gen_config["temperature"] = temperature
        if max_tokens:
            gen_config["maxOutputTokens"] = max_tokens
        if gen_config:
            payload["generationConfig"] = gen_config

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PlutoAI/2.0"
            }
        )

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        start_time = time.time()

        def sync_fetch():
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    with urllib.request.urlopen(req, timeout=40) as resp:
                        for line in resp:
                            decoded = line.decode("utf-8").strip()
                            if decoded.startswith("data: "):
                                try:
                                    chunk = json.loads(decoded[6:])
                                except Exception as json_err:
                                    logger.warning(f"Failed parsing Gemini SSE chunk: {json_err} | raw: {decoded[:150]}")
                                    continue

                                # Detect top-level error in stream chunk
                                if "error" in chunk:
                                    err_obj = chunk.get("error", {})
                                    err_code = err_obj.get("code", "UNKNOWN")
                                    err_message = err_obj.get("message", "Error chunk returned by Gemini")
                                    logger.error(f"Gemini SSE error chunk ({err_code}): {err_message}")
                                    asyncio.run_coroutine_threadsafe(
                                        queue.put(f"\n\n⚠️ **Gemini API Error ({err_code})**: {err_message}"),
                                        loop
                                    )
                                    continue

                                # Detect promptFeedback blocks (e.g. SAFETY, BLOCKLIST)
                                prompt_feedback = chunk.get("promptFeedback", {})
                                block_reason = prompt_feedback.get("blockReason")
                                if block_reason:
                                    logger.warning(f"Gemini promptFeedback blockReason: {block_reason}")
                                    asyncio.run_coroutine_threadsafe(
                                        queue.put(f"\n\n*(Content blocked by Gemini safety filter: {block_reason})*"),
                                        loop
                                    )

                                cands = chunk.get("candidates", [])
                                if cands:
                                    cand = cands[0]
                                    parts = cand.get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "text" in p and p["text"]:
                                            asyncio.run_coroutine_threadsafe(queue.put(p["text"]), loop)
                                    finish_reason = cand.get("finishReason")
                                    if finish_reason and finish_reason not in ["STOP", "MAX_TOKENS", None]:
                                        logger.warning(f"Gemini candidate finishReason: {finish_reason}")
                                        if finish_reason == "SAFETY":
                                            asyncio.run_coroutine_threadsafe(
                                                queue.put("\n\n*(Note: Output was modified according to safety guidelines)*"),
                                                loop
                                            )
                    elapsed = time.time() - start_time
                    logger.info(f"Gemini streaming completed successfully in {elapsed:.2f}s")
                    return
                except urllib.error.HTTPError as e:
                    if e.code in (503, 429) and attempt < max_retries:
                        logger.warning(f"Gemini temporary error {e.code}. Retrying attempt {attempt + 1}/{max_retries} after 1.5s...")
                        time.sleep(1.5)
                        continue
                    err_body = ""
                    try:
                        err_body = e.read().decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    logger.error(f"Gemini HTTPError {e.code}: {err_body}")

                err_msg = f"Gemini API returned error {e.code}"
                try:
                    err_json = json.loads(err_body)
                    detail = err_json.get("error", {}).get("message", "")
                    status_str = err_json.get("error", {}).get("status", "")
                    if e.code == 400 and ("API_KEY_INVALID" in err_body or "API key not valid" in detail):
                        err_msg = "Google Gemini API key is invalid. Please check your `GEMINI_API_KEY` configuration."
                    elif e.code == 429 or status_str == "RESOURCE_EXHAUSTED":
                        err_msg = "Google Gemini rate limit reached or quota exceeded. Please wait a moment and try again."
                    elif e.code == 404:
                        err_msg = f"Gemini model `{clean_model}` was not found. Please select Gemini 3.5 Flash."
                    elif detail:
                        err_msg = f"Google Gemini Error ({e.code}): {detail}"
                except Exception:
                    pass

                asyncio.run_coroutine_threadsafe(queue.put(f"\n\n**Error**: {err_msg}"), loop)
            except urllib.error.URLError as e:
                logger.error(f"Gemini URLError: {e.reason}")
                asyncio.run_coroutine_threadsafe(
                    queue.put(f"\n\n**Error**: Network connection error while communicating with Google Gemini: {str(e.reason)}"),
                    loop
                )
            except Exception as e:
                logger.exception("Unexpected error during Gemini stream")
                asyncio.run_coroutine_threadsafe(queue.put(f"\n\n**Error**: AI provider error: {str(e)}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop = asyncio.get_running_loop()
        threading_task = loop.run_in_executor(None, sync_fetch)

        token_count = 0
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                token_count += 1
                yield item
        finally:
            await threading_task

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        tokens = []
        async for token in self.stream_chat(messages, model, temperature, max_tokens):
            tokens.append(token)
        return "".join(tokens)
