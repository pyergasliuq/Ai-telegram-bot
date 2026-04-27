from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import (
    PLAN_DURATIONS,
    PLAN_PRICES_USD,
    TRIALS,
    Plan,
    settings,
)
from bot.core.i18n import t
from bot.db.models import Payment, Referral, User
from bot.handlers.keyboards import (
    crypto_assets_kb,
    durations_kb,
    methods_kb,
    plans_kb,
    trials_kb,
)
from bot.services.payments import (
    activate_subscription,
    create_stars_invoice,
    create_trial_invoice,
    crypto_bot,
    crypto_equivalents,
    format_crypto_line,
    has_active_subscription,
    stars_for_usd,
)
from bot.services.promo import already_used, apply_discount, find_active

log = logging.getLogger(__name__)
router = Router(name="billing")


@router.message(F.text.in_({"Улучшить или продлить подписку", "Upgrade or extend subscription"}))
async def show_plans(message: Message, lang: str) -> None:
    await message.answer(t(lang, "billing.choose_plan"), reply_markup=plans_kb(lang))


@router.callback_query(F.data.startswith("plan:"))
async def show_durations(cq: CallbackQuery, lang: str) -> None:
    plan = Plan(cq.data.split(":", 1)[1])
    text = t(lang, "billing.choose_duration", plan=plan.value.upper())
    await cq.message.edit_text(text, reply_markup=durations_kb(lang, plan))
    await cq.answer()


@router.callback_query(F.data.startswith("dur:"))
async def show_methods(cq: CallbackQuery, lang: str) -> None:
    _, plan_str, dur = cq.data.split(":")
    plan = Plan(plan_str)
    usd = PLAN_PRICES_USD[plan][dur]
    eq = await crypto_equivalents(usd)
    crypto_line = format_crypto_line(eq)
    stars = stars_for_usd(usd)
    line = t(
        lang,
        "billing.price_line",
        plan=plan.value.upper(),
        duration=dur,
        usd=str(usd),
        stars=stars,
        crypto=crypto_line,
    )
    body = line + "\n\n" + t(lang, "billing.choose_method")
    await cq.message.edit_text(body, reply_markup=methods_kb(lang, plan, dur))
    await cq.answer()


def _payload(method: str, plan: Plan, dur: str, user_id: int, *, trial: bool = False, asset: str = "") -> str:
    return json.dumps(
        {"m": method, "p": plan.value, "d": dur, "u": user_id, "t": int(trial), "a": asset},
        separators=(",", ":"),
    )


def _parse_payload(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


@router.callback_query(F.data.startswith("pay:stars:"))
async def pay_stars(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    _, _, plan_str, dur = cq.data.split(":")
    plan = Plan(plan_str)
    usd = PLAN_PRICES_USD[plan][dur]
    pending_code = (user.settings_data or {}).get("pending_promo")
    discount_promo = None
    if pending_code:
        promo = await find_active(session, pending_code)
        if promo and not await already_used(session, promo.id, user.telegram_id):
            usd = await apply_discount(session, promo, user.telegram_id, usd)
            discount_promo = pending_code
            data = dict(user.settings_data or {})
            data.pop("pending_promo", None)
            user.settings_data = data
    payload = _payload("stars", plan, dur, user.telegram_id)
    payment = Payment(
        user_id=user.id,
        plan=plan.value,
        duration_key=dur,
        method="stars",
        asset=None,
        amount_usd=float(usd),
        amount_native=str(stars_for_usd(usd)),
        status="pending",
        invoice_id=payload,
        extra={"promo": discount_promo} if discount_promo else {},
    )
    session.add(payment)
    await session.flush()
    await create_stars_invoice(cq.bot, cq.message.chat.id, plan, dur, usd, payload)
    await cq.message.answer(t(lang, "billing.invoice_sent"))
    await cq.answer()


@router.callback_query(F.data.startswith("pay:crypto:"))
async def pay_crypto_choose_asset(cq: CallbackQuery, lang: str) -> None:
    _, _, plan_str, dur = cq.data.split(":")
    plan = Plan(plan_str)
    await cq.message.edit_text(t(lang, "billing.choose_method"), reply_markup=crypto_assets_kb(lang, plan, dur))
    await cq.answer()


@router.callback_query(F.data.startswith("pay:cryptox:"))
async def pay_crypto_create(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    _, _, plan_str, dur, asset = cq.data.split(":")
    plan = Plan(plan_str)
    usd = PLAN_PRICES_USD[plan][dur]
    pending_code = (user.settings_data or {}).get("pending_promo")
    if pending_code:
        promo = await find_active(session, pending_code)
        if promo and not await already_used(session, promo.id, user.telegram_id):
            usd = await apply_discount(session, promo, user.telegram_id, usd)
            data = dict(user.settings_data or {})
            data.pop("pending_promo", None)
            user.settings_data = data
    eq = await crypto_equivalents(usd)
    amount = eq.get(asset, Decimal("0"))
    if not crypto_bot.available or amount <= 0:
        await cq.message.answer(t(lang, "billing.failed"))
        await cq.answer()
        return
    payload = _payload("crypto", plan, dur, user.telegram_id, asset=asset)
    description = f"{plan.value.upper()} {dur} subscription"
    invoice = await crypto_bot.create_invoice(asset=asset, amount=amount, description=description, payload=payload)
    payment = Payment(
        user_id=user.id,
        plan=plan.value,
        duration_key=dur,
        method="crypto",
        asset=asset,
        amount_usd=float(usd),
        amount_native=str(amount),
        status="pending",
        invoice_id=str(invoice.get("invoice_id")),
        extra={"pay_url": invoice.get("pay_url"), "payload": payload},
    )
    session.add(payment)
    await session.flush()
    pay_url = invoice.get("pay_url") or invoice.get("bot_invoice_url") or ""
    await cq.message.answer(t(lang, "billing.crypto_invoice", url=pay_url))
    await cq.answer()


@router.callback_query(F.data == "pay:manual")
async def pay_manual(cq: CallbackQuery, lang: str) -> None:
    await cq.message.answer(t(lang, "billing.manual", contact=settings.MANUAL_PAYMENT_CONTACT))
    await cq.answer()


@router.callback_query(F.data == "trial:menu")
async def trial_menu(cq: CallbackQuery, lang: str) -> None:
    await cq.message.edit_text(t(lang, "billing.trial.title"), reply_markup=trials_kb(lang))
    await cq.answer()


@router.callback_query(F.data.startswith("trial:"))
async def trial_buy(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    code = cq.data.split(":", 1)[1]
    if code == "menu":
        return
    plan_map = {"plus": Plan.PLUS, "pro": Plan.PRO, "max": Plan.MAX}
    plan = plan_map.get(code)
    if not plan:
        await cq.answer()
        return
    if plan.value in (user.trial_used_plans or []):
        await cq.message.answer(t(lang, "billing.trial.already_used", plan=plan.value.upper()))
        await cq.answer()
        return
    if await has_active_subscription(user):
        await cq.message.answer(t(lang, "billing.trial.has_active"))
        await cq.answer()
        return
    payload = _payload("stars", plan, "trial", user.telegram_id, trial=True)
    payment = Payment(
        user_id=user.id,
        plan=plan.value,
        duration_key="trial",
        method="stars",
        amount_usd=0.0,
        amount_native=str(TRIALS[plan]["stars"]),
        status="pending",
        invoice_id=payload,
        extra={"trial": True},
    )
    session.add(payment)
    await session.flush()
    await create_trial_invoice(cq.bot, cq.message.chat.id, plan, payload)
    await cq.answer()


@router.pre_checkout_query()
async def precheckout(pcq: PreCheckoutQuery) -> None:
    await pcq.bot.answer_pre_checkout_query(pcq.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    sp: SuccessfulPayment = message.successful_payment  # type: ignore[assignment]
    payload = _parse_payload(sp.invoice_payload or "")
    plan_str = payload.get("p")
    dur = payload.get("d", "")
    is_trial = bool(payload.get("t"))
    if not plan_str:
        await message.answer(t(lang, "billing.failed"))
        return
    plan = Plan(plan_str)
    if is_trial:
        days = TRIALS[plan]["days"]
        sub = await activate_subscription(session, user, plan, days, "stars", trial=True)
        await message.answer(t(lang, "billing.trial.activated", plan=plan.value.upper()))
    else:
        days = PLAN_DURATIONS.get(dur, 30)
        sub = await activate_subscription(session, user, plan, days, "stars", amount_usd=float(PLAN_PRICES_USD[plan].get(dur, 0)))
        await message.answer(
            t(lang, "billing.success", plan=plan.value.upper(), expires=sub.expires_at.strftime("%Y-%m-%d"))
        )

    payment_q = await session.execute(
        Payment.__table__.update()
        .where(Payment.invoice_id == (sp.invoice_payload or ""))
        .values(status="paid", updated_at=datetime.utcnow())
    )
    _ = payment_q
    await _credit_referrer_on_paid(session, user, days, is_trial)


async def _credit_referrer_on_paid(session: AsyncSession, user: User, duration_days: int, trial: bool) -> None:
    if trial or not user.referred_by:
        return
    from sqlalchemy import select

    inviter = (
        await session.execute(select(User).where(User.telegram_id == user.referred_by))
    ).scalar_one_or_none()
    if not inviter:
        return
    bonus_days = max(1, duration_days // 4)
    base = inviter.subscription_expires_at if (
        inviter.subscription_expires_at and inviter.subscription_expires_at > datetime.utcnow()
    ) else datetime.utcnow()
    from datetime import timedelta as _td

    inviter.subscription_expires_at = base + _td(days=bonus_days)
    if inviter.current_plan == Plan.FREE.value:
        inviter.current_plan = Plan.PLUS.value
    ref = (
        await session.execute(
            select(Referral).where(
                Referral.inviter_user_id == inviter.telegram_id,
                Referral.invited_user_id == user.telegram_id,
            )
        )
    ).scalar_one_or_none()
    if ref and not ref.paid_user:
        ref.paid_user = True
        ref.reward_type = "duration_bonus"
    await session.flush()


async def confirm_crypto_invoice(session: AsyncSession, payment: Payment) -> None:
    if payment.status == "paid":
        return
    payload = _parse_payload((payment.extra or {}).get("payload", ""))
    plan_str = payload.get("p")
    dur = payload.get("d", "")
    if not plan_str:
        return
    plan = Plan(plan_str)
    days = PLAN_DURATIONS.get(dur, 30)
    user = await session.get(User, payment.user_id)
    if not user:
        return
    await activate_subscription(
        session,
        user,
        plan,
        days,
        "crypto",
        amount_usd=payment.amount_usd or 0.0,
    )
    payment.status = "paid"
    await _credit_referrer_on_paid(session, user, days, trial=False)
    await session.flush()
