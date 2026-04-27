from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from bot.config.settings import settings


class ProviderError(Exception):
    pass


@dataclass
class ChatMessage:
    role: str
    content: str

    def to_openai(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1024


@dataclass
class ChatResponse:
    text: str
    provider: str = ""
    model: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageRequest:
    model: str
    prompt: str
    size: str = "1024x1024"


@dataclass
class ImageResponse:
    images: list[bytes]
    provider: str = ""
    model: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    name: str = ""
    base_url: str = ""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_S)

    async def chat(self, req: ChatRequest) -> ChatResponse:
        raise ProviderError(f"{self.name}: chat not implemented")

    async def image(self, req: ImageRequest) -> ImageResponse:
        raise ProviderError(f"{self.name}: image not implemented")


class OpenAICompatibleProvider(BaseProvider):
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"

    def _headers(self) -> dict[str, str]:
        return {
            self.auth_header: f"{self.auth_scheme} {self.api_key}".strip(),
            "Content-Type": "application/json",
        }

    async def chat(self, req: ChatRequest) -> ChatResponse:
        if not self.available:
            raise ProviderError(f"{self.name}: missing api key")
        payload = {
            "model": req.model,
            "messages": [m.to_openai() for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name}: {e}") from e

        if r.status_code == 429:
            raise ProviderError(f"{self.name}: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}")

        try:
            data = r.json()
        except ValueError as e:
            raise ProviderError(f"{self.name}: invalid json") from e

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"{self.name}: unexpected response shape") from e
        return ChatResponse(text=text, raw=data)
