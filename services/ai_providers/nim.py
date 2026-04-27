from __future__ import annotations

from services.ai_providers.base import OpenAICompatibleProvider


class NIMProvider(OpenAICompatibleProvider):
    name = "nim"
    base_url = "https://integrate.api.nvidia.com/v1"
