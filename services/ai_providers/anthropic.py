from __future__ import annotations

import httpx

from services.ai_providers.base import (
    BaseProvider,
    ChatRequest,
    ChatResponse,
    ProviderError,
)


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    base_url = "https://api.anthropic.com/v1"
    api_version = "2023-06-01"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    def _split_messages(self, req: ChatRequest) -> tuple[str, list[dict]]:
        system_parts: list[str] = []
        messages: list[dict] = []
        for m in req.messages:
            if m.role == "system":
                system_parts.append(m.content)
                continue
            role = "user" if m.role == "user" else "assistant"
            messages.append({"role": role, "content": m.content})
        return "\n\n".join(system_parts).strip(), messages

    async def chat(self, req: ChatRequest) -> ChatResponse:
        if not self.available:
            raise ProviderError("anthropic: missing api key")
        system, messages = self._split_messages(req)
        body: dict = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system
        url = f"{self.base_url.rstrip('/')}/messages"
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"anthropic: {e}") from e
        if r.status_code == 429:
            raise ProviderError("anthropic: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"anthropic: HTTP {r.status_code} {r.text[:200]}")
        try:
            data = r.json()
        except ValueError as e:
            raise ProviderError("anthropic: invalid json") from e
        try:
            blocks = data.get("content") or []
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (AttributeError, TypeError) as e:
            raise ProviderError("anthropic: unexpected response shape") from e
        return ChatResponse(text=text, raw=data)
