from __future__ import annotations

import base64

import httpx

from bot.services.ai_providers.base import (
    ImageRequest,
    ImageResponse,
    OpenAICompatibleProvider,
    ProviderError,
)


class TogetherProvider(OpenAICompatibleProvider):
    name = "together"
    base_url = "https://api.together.xyz/v1"

    async def image(self, req: ImageRequest) -> ImageResponse:
        if not self.available:
            raise ProviderError("together: missing api key")
        url = f"{self.base_url.rstrip('/')}/images/generations"
        try:
            w, h = (int(x) for x in req.size.split("x"))
        except ValueError:
            w, h = 1024, 1024
        body = {
            "model": req.model,
            "prompt": req.prompt,
            "width": w,
            "height": h,
            "n": 1,
            "response_format": "b64_json",
        }
        try:
            async with self._client() as cli:
                r = await cli.post(url, headers=self._headers(), json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"together: {e}") from e
        if r.status_code == 429:
            raise ProviderError("together: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"together: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        images: list[bytes] = []
        for entry in data.get("data", []):
            if entry.get("b64_json"):
                images.append(base64.b64decode(entry["b64_json"]))
            elif entry.get("url"):
                async with self._client() as cli:
                    img = await cli.get(entry["url"])
                if img.status_code == 200:
                    images.append(img.content)
        if not images:
            raise ProviderError("together: no image in response")
        return ImageResponse(images=images, raw=data)
