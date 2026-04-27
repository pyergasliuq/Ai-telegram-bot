from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

from bot.config.settings import CRYPTO_RATE_TTL_S, settings

log = logging.getLogger(__name__)


_COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "TON": "the-open-network",
    "USDT": "tether",
}


@dataclass
class _Cached:
    rates: dict[str, Decimal] = field(default_factory=dict)
    fetched_at: float = 0.0


_cache = _Cached()


async def get_usd_rates(assets: list[str]) -> dict[str, Decimal]:
    now = time.monotonic()
    if _cache.rates and now - _cache.fetched_at < CRYPTO_RATE_TTL_S:
        return {a: _cache.rates[a] for a in assets if a in _cache.rates}

    ids = ",".join({_COINGECKO_IDS[a] for a in assets if a in _COINGECKO_IDS})
    if not ids:
        return {}

    url = "https://api.coingecko.com/api/v3/simple/price"
    headers: dict[str, str] = {"accept": "application/json"}
    if settings.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY
    params = {"ids": ids, "vs_currencies": "usd"}
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("coingecko fetch failed: %s", e)
        return _cache.rates.copy()

    rates: dict[str, Decimal] = {}
    for asset, cg_id in _COINGECKO_IDS.items():
        entry = data.get(cg_id)
        if entry and "usd" in entry:
            rates[asset] = Decimal(str(entry["usd"]))
    if rates:
        _cache.rates.update(rates)
        _cache.fetched_at = now
    return {a: _cache.rates[a] for a in assets if a in _cache.rates}


def usd_to_crypto(usd: Decimal, asset: str, rates: dict[str, Decimal]) -> Decimal:
    rate = rates.get(asset)
    if not rate or rate <= 0:
        return Decimal("0")
    amount = usd / rate
    if asset == "BTC":
        return amount.quantize(Decimal("0.00000001"))
    if asset == "USDT":
        return amount.quantize(Decimal("0.01"))
    return amount.quantize(Decimal("0.0001"))
