import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from app.ai.base_provider import BaseAIProvider

logger = logging.getLogger("pluto.ai.openai")

class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def list_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "gpt-4o",
                "name": "GPT-4o (Omni)",
                "provider": "openai",
                "description": "OpenAI flagship high-intelligence multimodal model",
                "context_window": 128000,
                "supports_vision": True,
                "supports_streaming": True,
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "openai",
                "description": "Fast, cost-effective multimodal model for everyday tasks",
                "context_window": 128000,
                "supports_vision": True,
                "supports_streaming": True,
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "openai",
                "description": "Capable reasoning model with broad world knowledge",
                "context_window": 128000,
                "supports_vision": True,
                "supports_streaming": True,
            },
        ]

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            logger.info(f"Dispatching OpenAI stream request: model={model}, messages_count={len(messages)}")
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
            yield "\n\n**Error**: OpenAI authentication failed. Please check your `OPENAI_API_KEY` configuration."
        except RateLimitError:
            yield "\n\n**Error**: Rate limit exceeded or insufficient OpenAI credits. Please try again later."
        except APIConnectionError:
            yield "\n\n**Error**: Network connection error while communicating with OpenAI."
        except APIStatusError as e:
            yield f"\n\n**Error**: OpenAI returned status {e.status_code}: {e.message}"
        except Exception as e:
            logger.exception("Unexpected OpenAI stream error")
            yield f"\n\n**Error**: Unexpected AI provider error: {str(e)}"

    async def chat(
        self,
        messages: List[Dict[str, Any]],
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
            logger.exception("Unexpected OpenAI chat error")
            return f"Error: {str(e)}"
