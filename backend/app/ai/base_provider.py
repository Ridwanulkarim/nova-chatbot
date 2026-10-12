from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional

class BaseAIProvider(ABC):
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Yields text chunks as they arrive from the AI model."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Returns complete response text."""
        pass

    @abstractmethod
    def list_supported_models(self) -> List[Dict[str, Any]]:
        """Returns list of models supported by this provider."""
        pass
