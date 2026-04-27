from __future__ import annotations

from services.ai_providers.base import OpenAICompatibleProvider


class FireworksProvider(OpenAICompatibleProvider):
    name = "fireworks"
    base_url = "https://api.fireworks.ai/inference/v1"
