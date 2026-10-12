from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from app.ai.base_provider import BaseAIProvider

class GroqProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)

    def list_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "openai/gpt-oss-120b",
                "name": "GPT-OSS 120B (Groq)",
                "provider": "groq",
                "description": "Ultra-fast flagship open model accelerated on Groq LPU",
                "context_window": 128000,
                "supports_vision": False,
                "supports_streaming": True,
            },
            {
                "id": "qwen/qwen3.8-27b",
                "name": "Qwen 3.8 27B (Groq)",
                "provider": "groq",
                "description": "High-capability reasoning model running at blazing speed",
                "context_window": 128000,
                "supports_vision": False,
                "supports_streaming": True,
            },
            {
                "id": "openai/gpt-oss-20b",
                "name": "GPT-OSS 20B (Groq)",
                "provider": "groq",
                "description": "Instant lightweight model for rapid completions",
                "context_window": 64000,
                "supports_vision": False,
                "supports_streaming": True,
            },
        ]

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError:
            yield "\n\n**Error**: Groq authentication failed. Please verify your `GROQ_API_KEY`."
        except RateLimitError:
            yield "\n\n**Error**: Groq rate limit reached. Please wait a moment before trying again."
        except APIConnectionError:
            yield "\n\n**Error**: Connection issue communicating with Groq API endpoint."
        except APIStatusError as e:
            yield f"\n\n**Error**: Groq returned error code {e.status_code}: {e.message}"
        except Exception as e:
            yield f"\n\n**Error**: Provider error: {str(e)}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error: {str(e)}"
