from __future__ import annotations

from bot.services.ai_providers.base import OpenAICompatibleProvider


class SambaNovaProvider(OpenAICompatibleProvider):
    name = "sambanova"
    base_url = "https://api.sambanova.ai/v1"
