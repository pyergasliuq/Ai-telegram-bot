from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from bot.config.settings import (
    MODEL_REGISTRY,
    PLAN_PROVIDER_ACCESS,
    PROVIDERS,
    SPEED_TAG_MAP,
    Plan,
    SpeedMode,
    TaskType,
    settings,
)
from bot.core.rate_limit import provider_health
from bot.services.ai_providers import PROVIDER_CLIENTS, ProviderError
from bot.services.ai_providers.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImageRequest,
    ImageResponse,
)

log = logging.getLogger(__name__)


@dataclass
class RouteContext:
    plan: Plan
    task_type: TaskType
    speed_mode: SpeedMode = SpeedMode.BALANCE
    language: str = "ru"


class AllProvidersFailed(Exception):
    pass


def _candidates(plan: Plan, task_type: TaskType) -> list[tuple[str, str]]:
    return list(MODEL_REGISTRY.get(plan, {}).get(task_type, []))


def _provider_active(provider: str) -> bool:
    spec = PROVIDERS.get(provider)
    if not spec or not spec.get("active"):
        return False
    key_env = spec.get("key_env")
    if key_env is None:
        return True
    if provider == "cloudflare":
        return bool(getattr(settings, "CLOUDFLARE_API_KEY", "")) and bool(
            getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
        )
    if provider == "vertex":
        if not getattr(settings, "VERTEX_API_KEY", ""):
            return bool(getattr(settings, "GOOGLE_API_KEY", ""))
        return True
    return bool(getattr(settings, key_env, ""))


def _plan_allows_provider(plan: Plan, provider: str) -> bool:
    allowed = PLAN_PROVIDER_ACCESS.get(plan)
    if allowed is None:
        return True
    return provider in allowed


def _model_tags(provider: str, model: str) -> list[str]:
    spec = PROVIDERS.get(provider, {}).get("models", {}).get(model, {})
    tags = spec.get("tags") or []
    return list(tags)


def _score(provider: str, model: str, speed_mode: SpeedMode) -> int:
    tags = _model_tags(provider, model)
    desired = SPEED_TAG_MAP[speed_mode]
    score = 0
    if desired in tags:
        score += 100
    if speed_mode == SpeedMode.MAX and "reasoning" in tags:
        score += 30
    if speed_mode == SpeedMode.FAST and "fast" in tags:
        score += 20
    return score


def _ordered(plan: Plan, task_type: TaskType, speed_mode: SpeedMode) -> list[tuple[str, str]]:
    cands = [
        (p, m)
        for (p, m) in _candidates(plan, task_type)
        if _plan_allows_provider(plan, p) and _provider_active(p)
    ]
    cands.sort(key=lambda pm: _score(pm[0], pm[1], speed_mode), reverse=True)
    return cands


async def _try_call(
    provider: str,
    model: str,
    func: Callable[[Any, str], Awaitable[Any]],
    payload: Any,
) -> Any:
    client = PROVIDER_CLIENTS.get(provider)
    if client is None:
        raise ProviderError(f"unknown provider {provider}")
    return await func(client, payload, model)


async def chat(
    ctx: RouteContext,
    messages: list[ChatMessage],
    *,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> ChatResponse:
    candidates = _ordered(ctx.plan, ctx.task_type, ctx.speed_mode)
    if not candidates:
        raise AllProvidersFailed("no candidates configured")

    last_err: Exception | None = None
    for provider, model in candidates:
        if not provider_health.is_available(provider, model):
            continue
        client = PROVIDER_CLIENTS.get(provider)
        if client is None:
            continue
        try:
            req = ChatRequest(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            resp = await client.chat(req)
            provider_health.mark_success(provider, model)
            resp.provider = provider
            resp.model = model
            return resp
        except ProviderError as e:
            last_err = e
            log.warning("provider %s model %s failed: %s", provider, model, e)
            provider_health.mark_failure(provider, model, settings.PROVIDER_COOLDOWN_S)
            continue
        except Exception as e:
            last_err = e
            log.exception("unexpected error in %s/%s", provider, model)
            provider_health.mark_failure(provider, model, settings.PROVIDER_COOLDOWN_S)
            continue
    raise AllProvidersFailed(str(last_err) if last_err else "all providers exhausted")


async def image(
    ctx: RouteContext,
    prompt: str,
    *,
    size: str = "1024x1024",
) -> ImageResponse:
    candidates = _ordered(ctx.plan, TaskType.IMAGE, ctx.speed_mode)
    last_err: Exception | None = None
    for provider, model in candidates:
        if not provider_health.is_available(provider, model):
            continue
        client = PROVIDER_CLIENTS.get(provider)
        if client is None or not hasattr(client, "image"):
            continue
        try:
            req = ImageRequest(model=model, prompt=prompt, size=size)
            resp = await client.image(req)
            provider_health.mark_success(provider, model)
            resp.provider = provider
            resp.model = model
            return resp
        except ProviderError as e:
            last_err = e
            log.warning("image provider %s/%s failed: %s", provider, model, e)
            provider_health.mark_failure(provider, model, settings.PROVIDER_COOLDOWN_S)
            continue
        except Exception as e:
            last_err = e
            log.exception("image unexpected error %s/%s", provider, model)
            provider_health.mark_failure(provider, model, settings.PROVIDER_COOLDOWN_S)
            continue
    raise AllProvidersFailed(str(last_err) if last_err else "no image providers available")
