from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from aiocryptopay import AioCryptoPay, Networks
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
        self.testnet = testnet
        self._client: AioCryptoPay | None = None

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _ensure(self) -> AioCryptoPay:
        if self._client is None:
            network = Networks.TEST_NET if self.testnet else Networks.MAIN_NET
            self._client = AioCryptoPay(token=self.token, network=network)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                log.exception("crypto-bot close failed")
            self._client = None

    async def create_invoice(
        self,
        asset: str,
        amount: Decimal,
        description: str,
        payload: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("crypto-bot: missing token")
        cli = self._ensure()
        invoice = await cli.create_invoice(
            asset=asset,
            amount=float(amount),
            description=description,
            payload=payload,
            expires_in=expires_in,
            hidden_message="Спасибо за оплату!",
            allow_comments=False,
            allow_anonymous=True,
        )
        return _invoice_to_dict(invoice)

    async def get_invoices(self, invoice_ids: list[str]) -> list[dict[str, Any]]:
        if not self.available:
            raise RuntimeError("crypto-bot: missing token")
        cli = self._ensure()
        ids = [int(x) for x in invoice_ids if str(x).isdigit()]
        invoices = await cli.get_invoices(invoice_ids=ids) if ids else await cli.get_invoices()
        if not isinstance(invoices, list):
            invoices = [invoices] if invoices else []
        return [_invoice_to_dict(i) for i in invoices]


def _invoice_to_dict(inv: Any) -> dict[str, Any]:
    if isinstance(inv, dict):
        return inv
    keys = (
        "invoice_id",
        "status",
        "asset",
        "amount",
        "pay_url",
        "bot_invoice_url",
        "mini_app_invoice_url",
        "web_app_invoice_url",
        "payload",
        "description",
        "created_at",
        "paid_at",
    )
    data: dict[str, Any] = {}
    for k in keys:
        if hasattr(inv, k):
            v = getattr(inv, k)
            data[k] = v
    return data


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
