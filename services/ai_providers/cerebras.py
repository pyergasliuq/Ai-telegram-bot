from __future__ import annotations

from services.ai_providers.base import OpenAICompatibleProvider


class CerebrasProvider(OpenAICompatibleProvider):
    name = "cerebras"
    base_url = "https://api.cerebras.ai/v1"
