from __future__ import annotations

from bot.services.ai_providers.google import GoogleProvider


class VertexProvider(GoogleProvider):
    name = "vertex"

    def __init__(
        self,
        api_key: str,
        project: str = "",
        location: str = "us-central1",
        fallback_api_key: str = "",
    ) -> None:
        effective = api_key or fallback_api_key
        super().__init__(api_key=effective)
        self.project = project
        self.location = location
