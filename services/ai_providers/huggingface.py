from __future__ import annotations

import httpx

from services.ai_providers.base import (
    BaseProvider,
    ChatRequest,
    ChatResponse,
    ProviderError,
)


class HuggingfaceProvider(BaseProvider):
    name = "huggingface"
    base_url = "https://api-inference.huggingface.co"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, req: ChatRequest) -> ChatResponse:
        if not self.available:
            raise ProviderError("huggingface: missing api key")
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        body = {
            "model": req.model,
            "messages": [m.to_openai() for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"huggingface: {e}") from e
        if r.status_code == 429:
            raise ProviderError("huggingface: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"huggingface: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("huggingface: unexpected response shape") from e
        return ChatResponse(text=text, raw=data)
