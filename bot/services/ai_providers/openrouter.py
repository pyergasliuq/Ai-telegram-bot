from __future__ import annotations

from bot.services.ai_providers.base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def _headers(self) -> dict[str, str]:
        h = super()._headers()
        h["HTTP-Referer"] = "https://t.me"
        h["X-Title"] = "Ai-telegram-bot"
        return h
