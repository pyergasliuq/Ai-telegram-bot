from __future__ import annotations

import httpx

from bot.services.ai_providers.base import (
    BaseProvider,
    ChatRequest,
    ChatResponse,
    ImageRequest,
    ImageResponse,
    ProviderError,
)


class CloudflareProvider(BaseProvider):
    name = "cloudflare"

    def __init__(self, api_key: str, account_id: str) -> None:
        super().__init__(api_key=api_key)
        self.account_id = account_id

    @property
    def available(self) -> bool:
        return bool(self.api_key) and bool(self.account_id)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _model_url(self, model: str) -> str:
        return f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model}"

    async def chat(self, req: ChatRequest) -> ChatResponse:
        if not self.available:
            raise ProviderError("cloudflare: missing api key/account_id")
        url = self._model_url(req.model)
        body = {
            "messages": [m.to_openai() for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"cloudflare: {e}") from e
        if r.status_code == 429:
            raise ProviderError("cloudflare: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"cloudflare: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        result = data.get("result") or {}
        text = ""
        if isinstance(result, dict):
            text = result.get("response") or ""
            if not text and "choices" in result:
                try:
                    text = result["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    text = ""
        if not text:
            raise ProviderError("cloudflare: empty response")
        return ChatResponse(text=text, raw=data)

    async def image(self, req: ImageRequest) -> ImageResponse:
        if not self.available:
            raise ProviderError("cloudflare: missing api key/account_id")
        url = self._model_url(req.model)
        body = {"prompt": req.prompt}
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"cloudflare: {e}") from e
        if r.status_code >= 400:
            raise ProviderError(f"cloudflare: HTTP {r.status_code} {r.text[:200]}")
        ct = r.headers.get("content-type", "")
        if ct.startswith("image/"):
            return ImageResponse(images=[r.content], raw={})
        try:
            data = r.json()
        except ValueError as e:
            raise ProviderError("cloudflare: invalid image response") from e
        result = data.get("result") or {}
        b64 = result.get("image") if isinstance(result, dict) else None
        if not b64:
            raise ProviderError("cloudflare: no image in response")
        import base64

        return ImageResponse(images=[base64.b64decode(b64)], raw=data)
