from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from bot.config.settings import ANTISPAM, PLAN_LIMITS, Plan


@dataclass
class _UserState:
    timestamps: deque[float] = field(default_factory=deque)
    minute_window: deque[float] = field(default_factory=deque)
    cooldown_until: float = 0.0
    pending: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RateLimiter:
    def __init__(self) -> None:
        self._state: dict[int, _UserState] = defaultdict(_UserState)

    def _get(self, user_id: int) -> _UserState:
        return self._state[user_id]

    async def check_message(self, user_id: int, plan: Plan) -> tuple[bool, str | None]:
        st = self._get(user_id)
        async with st.lock:
            now = time.monotonic()
            if now < st.cooldown_until:
                return False, "antispam.too_fast"

            window = ANTISPAM["burst_window_s"]
            limit = ANTISPAM["burst_max"]
            while st.timestamps and now - st.timestamps[0] > window:
                st.timestamps.popleft()
            if len(st.timestamps) >= limit:
                st.cooldown_until = now + ANTISPAM["cooldown_s"]
                return False, "antispam.too_fast"

            rpm = PLAN_LIMITS[plan]["rpm"]
            while st.minute_window and now - st.minute_window[0] > 60:
                st.minute_window.popleft()
            if len(st.minute_window) >= rpm:
                return False, "antispam.too_fast"

            if st.pending >= ANTISPAM["max_pending_per_user"]:
                return False, "antispam.busy"

            st.timestamps.append(now)
            st.minute_window.append(now)
            return True, None

    async def acquire_pending(self, user_id: int) -> None:
        st = self._get(user_id)
        async with st.lock:
            st.pending += 1

    async def release_pending(self, user_id: int) -> None:
        st = self._get(user_id)
        async with st.lock:
            if st.pending > 0:
                st.pending -= 1


rate_limiter = RateLimiter()


@dataclass
class _ProviderHealth:
    cooldown_until: float = 0.0
    fail_count: int = 0


class ProviderHealth:
    def __init__(self) -> None:
        self._state: dict[tuple[str, str], _ProviderHealth] = defaultdict(_ProviderHealth)

    def is_available(self, provider: str, model: str) -> bool:
        st = self._state[(provider, model)]
        return time.monotonic() >= st.cooldown_until

    def mark_failure(self, provider: str, model: str, cooldown_s: int) -> None:
        st = self._state[(provider, model)]
        st.fail_count += 1
        st.cooldown_until = time.monotonic() + cooldown_s

    def mark_success(self, provider: str, model: str) -> None:
        st = self._state[(provider, model)]
        st.fail_count = 0
        st.cooldown_until = 0.0


provider_health = ProviderHealth()
