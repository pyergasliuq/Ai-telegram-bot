from __future__ import annotations

from services.ai_providers.base import OpenAICompatibleProvider


class GitHubModelsProvider(OpenAICompatibleProvider):
    name = "github_models"
    base_url = "https://models.github.ai/inference"
