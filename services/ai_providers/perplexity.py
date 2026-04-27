from __future__ import annotations

from services.ai_providers.base import OpenAICompatibleProvider


class PerplexityProvider(OpenAICompatibleProvider):
    name = "perplexity"
    base_url = "https://api.perplexity.ai"
