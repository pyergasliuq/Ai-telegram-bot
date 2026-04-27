from __future__ import annotations

import base64

import httpx

from services.ai_providers.base import (
    BaseProvider,
    ChatRequest,
    ChatResponse,
    ImageRequest,
    ImageResponse,
    ProviderError,
)


class GoogleProvider(BaseProvider):
    name = "google"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _to_contents(self, req: ChatRequest) -> tuple[list[dict], dict | None]:
        contents: list[dict] = []
        system: dict | None = None
        for m in req.messages:
            if m.role == "system":
                system = {"parts": [{"text": m.content}]}
                continue
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents, system

    async def chat(self, req: ChatRequest) -> ChatResponse:
        if not self.available:
            raise ProviderError("google: missing api key")
        contents, system = self._to_contents(req)
        url = f"{self.base_url}/models/{req.model}:generateContent"
        params = {"key": self.api_key}
        body: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = system
        try:
            async with self._client() as cli:
                r = await cli.post(url, params=params, json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"google: {e}") from e
        if r.status_code == 429:
            raise ProviderError("google: 429 rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"google: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("google: unexpected response shape") from e
        return ChatResponse(text=text, raw=data)

    async def image(self, req: ImageRequest) -> ImageResponse:
        if not self.available:
            raise ProviderError("google: missing api key")
        url = f"{self.base_url}/models/{req.model}:generateContent"
        params = {"key": self.api_key}
        body = {
            "contents": [{"role": "user", "parts": [{"text": req.prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        try:
            async with self._client() as cli:
                r = await cli.post(url, params=params, json=body)
        except httpx.HTTPError as e:
            raise ProviderError(f"google: {e}") from e
        if r.status_code >= 400:
            raise ProviderError(f"google: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        images: list[bytes] = []
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    images.append(base64.b64decode(inline["data"]))
        if not images:
            raise ProviderError("google: no image in response")
        return ImageResponse(images=images, raw=data)
