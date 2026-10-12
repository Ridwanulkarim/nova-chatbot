from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.ai.base_provider import BaseAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider

class AIProviderFactory:
    def __init__(self):
        self._providers: Dict[str, BaseAIProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        # Initialize OpenAI if key is present
        if settings.OPENAI_API_KEY:
            self._providers["openai"] = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )

        # Initialize Groq if key is present
        if settings.GROQ_API_KEY:
            self._providers["groq"] = GroqProvider(
                api_key=settings.GROQ_API_KEY
            )

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[BaseAIProvider]:
        if not provider_name:
            provider_name = settings.DEFAULT_PROVIDER
        
        # If requested provider is configured, return it
        if provider_name in self._providers:
            return self._providers[provider_name]
        
        # Fallback to any configured provider if the requested one is missing
        if self._providers:
            return next(iter(self._providers.values()))
            
        return None

    def get_provider_for_model(self, model_id: str) -> Tuple[Optional[BaseAIProvider], str]:
        """Resolves the provider and normalized model ID."""
        for provider_name, provider in self._providers.items():
            for m in provider.list_supported_models():
                if m["id"] == model_id:
                    return provider, model_id
        
        # If model is not explicitly listed, use default provider and fallback to its first supported model
        provider = self.get_provider()
        if provider:
            supported = provider.list_supported_models()
            if supported:
                return provider, supported[0]["id"]
        return provider, model_id

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Returns ONLY models from providers that have active credentials configured."""
        available = []
        for provider in self._providers.values():
            available.extend(provider.list_supported_models())
        return available

    def has_any_provider(self) -> bool:
        return len(self._providers) > 0

ai_factory = AIProviderFactory()
