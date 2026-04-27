from __future__ import annotations

import base64

import httpx

from services.ai_providers.base import (
    ImageRequest,
    ImageResponse,
    OpenAICompatibleProvider,
    ProviderError,
)


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1"

    async def image(self, req: ImageRequest) -> ImageResponse:
        if not self.available:
            raise ProviderError("openai: missing api key")
        url = f"{self.base_url.rstrip('/')}/images/generations"
        body = {
            "model": req.model,
            "prompt": req.prompt,
            "size": req.size,
            "response_format": "b64_json",
            "n": 1,
        }
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"openai: {e}") from e
        if r.status_code == 429:
            raise ProviderError("openai: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"openai: HTTP {r.status_code} {r.text[:200]}")
        try:
            data = r.json()
        except ValueError as e:
            raise ProviderError("openai: invalid json") from e
        items = data.get("data") or []
        images: list[bytes] = []
        for it in items:
            b64 = it.get("b64_json")
            if b64:
                images.append(base64.b64decode(b64))
        if not images:
            raise ProviderError("openai: no image in response")
        return ImageResponse(images=images, raw=data)
