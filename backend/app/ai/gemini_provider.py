import json
import urllib.request
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.ai.base_provider import BaseAIProvider

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "gemini-3.5-flash",
                "name": "Gemini 3.5 Flash (Google)",
                "provider": "gemini",
                "description": "Google flagship fast multimodal model with native vision and reasoning",
                "context_window": 1048576,
                "supports_vision": True,
                "supports_streaming": True,
            },
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash (Google)",
                "provider": "gemini",
                "description": "Ultra-fast multimodal model for quick responses and question solving",
                "context_window": 1048576,
                "supports_vision": True,
                "supports_streaming": True,
            }
        ]

    def _convert_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        system_instructions = []
        contents = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")

            if role == "system":
                system_instructions.append(content)
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            else:
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })

        payload: Dict[str, Any] = {"contents": contents}

        if system_instructions:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_instructions)}]
            }

        return payload

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        clean_model = model.replace("google/", "").replace("models/", "").strip()
        if not clean_model:
            clean_model = "gemini-3.5-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._convert_messages(messages)
        if temperature:
            payload["generationConfig"] = {"temperature": temperature}
            if max_tokens:
                payload["generationConfig"]["maxOutputTokens"] = max_tokens

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def sync_fetch():
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    for line in resp:
                        decoded = line.decode("utf-8").strip()
                        if decoded.startswith("data: "):
                            try:
                                chunk = json.loads(decoded[6:])
                                cands = chunk.get("candidates", [])
                                if cands:
                                    parts = cands[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "text" in p and p["text"]:
                                            asyncio.run_coroutine_threadsafe(queue.put(p["text"]), loop)
                            except Exception:
                                continue
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(f"\n\n**Error**: Google Gemini connection error: {str(e)}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop = asyncio.get_running_loop()
        threading_task = loop.run_in_executor(None, sync_fetch)

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await threading_task

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        tokens = []
        async for token in self.stream_chat(messages, model, temperature, max_tokens):
            tokens.append(token)
        return "".join(tokens)
