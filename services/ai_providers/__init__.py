from __future__ import annotations

from services.ai_providers.anthropic import AnthropicProvider
from services.ai_providers.base import (
    BaseProvider,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImageRequest,
    ImageResponse,
    ProviderError,
)
from services.ai_providers.cerebras import CerebrasProvider
from services.ai_providers.cloudflare import CloudflareProvider
from services.ai_providers.fireworks import FireworksProvider
from services.ai_providers.github_models import GitHubModelsProvider
from services.ai_providers.google import GoogleProvider
from services.ai_providers.groq import GroqProvider
from services.ai_providers.huggingface import HuggingfaceProvider
from services.ai_providers.nim import NIMProvider
from services.ai_providers.onlysq import OnlySQProvider
from services.ai_providers.openai import OpenAIProvider
from services.ai_providers.openrouter import OpenRouterProvider
from services.ai_providers.perplexity import PerplexityProvider
from services.ai_providers.sambanova import SambaNovaProvider
from services.ai_providers.together import TogetherProvider
from services.ai_providers.vertex import VertexProvider
from settings import PROVIDERS, settings


def _build() -> dict[str, BaseProvider]:
    return {
        "google": GoogleProvider(api_key=settings.GOOGLE_API_KEY),
        "groq": GroqProvider(
            api_key=settings.GROQ_API_KEY,
            base_url=PROVIDERS["groq"]["base_url"],
        ),
        "openrouter": OpenRouterProvider(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=PROVIDERS["openrouter"]["base_url"],
        ),
        "huggingface": HuggingfaceProvider(
            api_key=settings.HUGGINGFACE_API_KEY,
            base_url=PROVIDERS["huggingface"]["base_url"],
        ),
        "onlysq": OnlySQProvider(
            api_key=settings.ONLYSQ_API_KEY,
            base_url=PROVIDERS["onlysq"]["base_url"],
        ),
        "together": TogetherProvider(
            api_key=settings.TOGETHER_API_KEY,
            base_url=PROVIDERS["together"]["base_url"],
        ),
        "cerebras": CerebrasProvider(
            api_key=settings.CEREBRAS_API_KEY,
            base_url=PROVIDERS["cerebras"]["base_url"],
        ),
        "sambanova": SambaNovaProvider(
            api_key=settings.SAMBANOVA_API_KEY,
            base_url=PROVIDERS["sambanova"]["base_url"],
        ),
        "cloudflare": CloudflareProvider(
            api_key=settings.CLOUDFLARE_API_KEY,
            account_id=settings.CLOUDFLARE_ACCOUNT_ID,
        ),
        "fireworks": FireworksProvider(
            api_key=settings.FIREWORKS_API_KEY,
            base_url=PROVIDERS["fireworks"]["base_url"],
        ),
        "github_models": GitHubModelsProvider(
            api_key=settings.GITHUB_MODELS_API_KEY,
            base_url=PROVIDERS["github_models"]["base_url"],
        ),
        "nim": NIMProvider(
            api_key=settings.NVIDIA_API_KEY,
            base_url=PROVIDERS["nim"]["base_url"],
        ),
        "openai": OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            base_url=PROVIDERS["openai"]["base_url"],
        ),
        "anthropic": AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=PROVIDERS["anthropic"]["base_url"],
        ),
        "vertex": VertexProvider(
            api_key=settings.VERTEX_API_KEY,
            project=settings.VERTEX_PROJECT,
            location=settings.VERTEX_LOCATION,
            fallback_api_key=settings.GOOGLE_API_KEY,
        ),
        "perplexity": PerplexityProvider(
            api_key=settings.PERPLEXITY_API_KEY,
            base_url=PROVIDERS["perplexity"]["base_url"],
        ),
    }


PROVIDER_CLIENTS: dict[str, BaseProvider] = _build()


__all__ = [
    "PROVIDER_CLIENTS",
    "BaseProvider",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ImageRequest",
    "ImageResponse",
    "ProviderError",
]
