from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.ai.base_provider import BaseAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider
from app.ai.gemini_provider import GeminiProvider

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

        # Initialize Gemini if key is present
        if settings.GEMINI_API_KEY:
            self._providers["gemini"] = GeminiProvider(
                api_key=settings.GEMINI_API_KEY
            )

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[BaseAIProvider]:
        if not self._providers:
            self._initialize_providers()

        if not provider_name:
            provider_name = settings.DEFAULT_PROVIDER
        
        # If requested provider is configured, return it
        if provider_name in self._providers:
            return self._providers[provider_name]
        
        # If gemini is available, prefer it as top general-purpose provider
        if "gemini" in self._providers:
            return self._providers["gemini"]

        # Fallback to any configured provider
        if self._providers:
            return next(iter(self._providers.values()))
            
        return None

    def get_provider_for_model(self, model_id: str) -> Tuple[Optional[BaseAIProvider], str]:
        """Resolves the provider and normalized model ID."""
        if not self._providers:
            self._initialize_providers()

        # Handle aliases
        if model_id in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]:
            model_id = "gemini-3.5-flash"

        for provider_name, provider in self._providers.items():
            for m in provider.list_supported_models():
                if m["id"] == model_id:
                    return provider, model_id
        
        # Check if model has gemini prefix or name
        if "gemini" in model_id.lower() and "gemini" in self._providers:
            return self._providers["gemini"], "gemini-3.5-flash"

        # Check if model has gpt prefix and openai is available
        if ("gpt" in model_id.lower() or "o1" in model_id.lower() or "o3" in model_id.lower()) and "openai" in self._providers:
            return self._providers["openai"], model_id

        # Fallback to default provider
        provider = self.get_provider()
        if provider:
            supported = provider.list_supported_models()
            if supported:
                return provider, supported[0]["id"]
        return provider, model_id

    def get_vision_capable_provider(self, requested_model: Optional[str] = None) -> Tuple[Optional[BaseAIProvider], str]:
        """
        Guarantees selection of a genuinely vision-capable model when images are present.
        If the user requested a vision model, honors it.
        Otherwise, routes to Gemini 3.5 Flash (or OpenAI GPT-4o).
        """
        if not self._providers:
            self._initialize_providers()

        # 1. If requested model itself supports vision, use it
        if requested_model:
            provider, norm_model = self.get_provider_for_model(requested_model)
            if provider:
                for m in provider.list_supported_models():
                    if m["id"] == norm_model and m.get("supports_vision"):
                        return provider, norm_model

        # 2. Prioritize Gemini if available (fast, native vision, generous context)
        if "gemini" in self._providers:
            return self._providers["gemini"], "gemini-3.5-flash"

        # 3. Check OpenAI if available
        if "openai" in self._providers:
            oa_p = self._providers["openai"]
            for m in oa_p.list_supported_models():
                if m.get("supports_vision"):
                    return oa_p, m["id"]

        # 4. Fallback to default
        return self.get_provider_for_model(requested_model or settings.DEFAULT_MODEL)

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Returns ONLY models from providers that have active credentials configured."""
        if not self._providers:
            self._initialize_providers()

        available = []
        for provider in self._providers.values():
            available.extend(provider.list_supported_models())
        return available

    def has_any_provider(self) -> bool:
        if not self._providers:
            self._initialize_providers()
        return len(self._providers) > 0

ai_factory = AIProviderFactory()
