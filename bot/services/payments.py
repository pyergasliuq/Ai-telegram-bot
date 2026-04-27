from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import (
    CRYPTO_ASSETS,
    PLAN_DURATIONS,
    PLAN_PRICES_USD,
    STARS_PER_USD,
    TRIALS,
    Plan,
    settings,
)
from bot.db.models import Payment, Subscription, User
from bot.services.crypto_rates import get_usd_rates, usd_to_crypto

log = logging.getLogger(__name__)


def stars_for_usd(usd: Decimal) -> int:
    return max(1, int((usd * STARS_PER_USD).to_integral_value()))


def price_table(plan: Plan) -> dict[str, Decimal]:
    return PLAN_PRICES_USD.get(plan, {})


async def crypto_equivalents(usd: Decimal) -> dict[str, Decimal]:
    rates = await get_usd_rates(CRYPTO_ASSETS)
    return {a: usd_to_crypto(usd, a, rates) for a in CRYPTO_ASSETS}


def format_crypto_line(eq: dict[str, Decimal]) -> str:
    parts: list[str] = []
    for asset in CRYPTO_ASSETS:
        amt = eq.get(asset)
        if amt and amt > 0:
            parts.append(f"{amt} {asset}")
    return " | ".join(parts) if parts else "—"


async def create_stars_invoice(
    bot: Bot,
    chat_id: int,
    plan: Plan,
    duration_key: str,
    usd_price: Decimal,
    payload: str,
) -> None:
    title = f"{plan.value.upper()} {duration_key}"
    description = f"Подписка {plan.value.upper()} на {PLAN_DURATIONS[duration_key]} дней."
    stars = stars_for_usd(usd_price)
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=stars)],
        provider_token="",
    )


async def create_trial_invoice(bot: Bot, chat_id: int, plan: Plan, payload: str) -> None:
    cfg = TRIALS.get(plan)
    if not cfg:
        return
    title = f"Trial {plan.value.upper()} 3d"
    description = f"Пробный период {plan.value.upper()} на {cfg['days']} дней."
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=cfg["stars"])],
        provider_token="",
    )


class CryptoBotClient:
    def __init__(self, token: str, testnet: bool = False) -> None:
        self.token = token
        self.base_url = (
            "https://testnet-pay.crypt.bot/api" if testnet else "https://pay.crypt.bot/api"
        )

    @property
    def available(self) -> bool:
        return bool(self.token)

    async def _request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("crypto-bot: missing token")
        headers = {"Crypto-Pay-API-Token": self.token, "Content-Type": "application/json"}
        url = f"{self.base_url}/{method}"
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.post(url, headers=headers, json=payload or {})
        if r.status_code >= 400:
            raise RuntimeError(f"crypto-bot: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"crypto-bot: {data}")
        return data["result"]

    async def create_invoice(
        self,
        asset: str,
        amount: Decimal,
        description: str,
        payload: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        body = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "hidden_message": "Спасибо за оплату!",
            "payload": payload,
            "expires_in": expires_in,
            "allow_comments": False,
            "allow_anonymous": True,
        }
        return await self._request("createInvoice", body)

    async def get_invoices(self, invoice_ids: list[str]) -> list[dict[str, Any]]:
        body = {"invoice_ids": ",".join(invoice_ids)} if invoice_ids else {}
        result = await self._request("getInvoices", body)
        items = result.get("items") if isinstance(result, dict) else result
        return list(items or [])


crypto_bot = CryptoBotClient(token=settings.CRYPTO_BOT_TOKEN, testnet=settings.CRYPTO_BOT_TESTNET)


async def activate_subscription(
    session: AsyncSession,
    user: User,
    plan: Plan,
    duration_days: int,
    method: str,
    *,
    trial: bool = False,
    promo_code: str | None = None,
    amount_usd: float = 0.0,
) -> Subscription:
    now = datetime.utcnow()
    base = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
    expires = base + timedelta(days=duration_days)
    sub = Subscription(
        user_id=user.id,
        plan=plan.value,
        starts_at=now,
        expires_at=expires,
        payment_method=method,
        duration_days=duration_days,
        trial=trial,
        promo_code=promo_code,
        amount_usd=amount_usd,
    )
    session.add(sub)
    user.current_plan = plan.value
    user.subscription_expires_at = expires
    if trial:
        used = list(user.trial_used_plans or [])
        if plan.value not in used:
            used.append(plan.value)
            user.trial_used_plans = used
    await session.flush()
    return sub


async def has_active_subscription(user: User) -> bool:
    return bool(
        user.subscription_expires_at
        and user.subscription_expires_at > datetime.utcnow()
        and user.current_plan != Plan.FREE.value
    )


async def get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    return await session.get(Payment, payment_id)


async def get_payment_by_invoice(session: AsyncSession, invoice_id: str) -> Payment | None:
    stmt = select(Payment).where(Payment.invoice_id == invoice_id)
    return (await session.execute(stmt)).scalar_one_or_none()
