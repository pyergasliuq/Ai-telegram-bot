from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PromoCode, PromoUsage, Referral, User
from settings import (
    PROMO_DISCOUNT_MAX,
    PROMO_DISCOUNT_MIN,
    REFERRAL_PROMO_THRESHOLD,
    USER_PROMO_DISCOUNT_MAX,
    USER_PROMO_DISCOUNT_MIN,
    Plan,
)

CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,16}$")


class PromoError(Exception):
    pass


async def find_active(session: AsyncSession, code: str) -> PromoCode | None:
    stmt = select(PromoCode).where(PromoCode.code == code, PromoCode.active.is_(True))
    promo = (await session.execute(stmt)).scalar_one_or_none()
    if not promo:
        return None
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return None
    if promo.max_uses and promo.used_count >= promo.max_uses:
        return None
    return promo


async def already_used(session: AsyncSession, promo_id: int, user_id: int) -> bool:
    stmt = select(PromoUsage).where(PromoUsage.promo_id == promo_id, PromoUsage.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


def check_user_eligible(promo: PromoCode, user: User) -> None:
    now = datetime.utcnow()
    has_active = bool(
        user.subscription_expires_at
        and user.subscription_expires_at > now
        and user.current_plan != Plan.FREE.value
    )
    if promo.requires_active_subscription and not has_active:
        raise PromoError("active subscription required")
    if promo.sponsor_only and not has_active:
        raise PromoError("sponsor-only code requires active subscription")
    if promo.min_plan_required:
        order = [Plan.FREE.value, Plan.PLUS.value, Plan.PRO.value, Plan.MAX.value]
        try:
            min_idx = order.index(promo.min_plan_required)
            cur_idx = order.index(user.current_plan)
        except ValueError:
            return
        if cur_idx < min_idx:
            raise PromoError("plan too low for this promo")


async def apply_discount(
    session: AsyncSession,
    promo: PromoCode,
    user_id: int,
    amount_usd: Decimal,
    user: User | None = None,
) -> Decimal:
    if user is not None:
        check_user_eligible(promo, user)
    promo.used_count += 1
    session.add(PromoUsage(promo_id=promo.id, user_id=user_id))
    await session.flush()
    discount = (amount_usd * promo.discount_percent) / Decimal(100)
    return (amount_usd - discount).quantize(Decimal("0.01"))


async def paid_referral_count(session: AsyncSession, inviter_id: int) -> int:
    stmt = select(func.count(Referral.id)).where(
        Referral.inviter_user_id == inviter_id, Referral.paid_user.is_(True)
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def can_create_user_promo(session: AsyncSession, user: User) -> bool:
    return (await paid_referral_count(session, user.telegram_id)) >= REFERRAL_PROMO_THRESHOLD


async def create_user_promo(
    session: AsyncSession,
    user: User,
    code: str,
    discount: int,
    description: str | None = None,
) -> PromoCode:
    if not CODE_RE.match(code):
        raise PromoError("invalid code format")
    if discount < USER_PROMO_DISCOUNT_MIN or discount > USER_PROMO_DISCOUNT_MAX:
        raise PromoError("invalid discount")
    if not await can_create_user_promo(session, user):
        raise PromoError("not enough paid referrals")
    if await find_active(session, code):
        raise PromoError("code exists")
    promo = PromoCode(
        code=code,
        discount_percent=discount,
        description=description or f"User promo by {user.telegram_id}",
        creator_user_id=user.telegram_id,
        is_user_referral=True,
        active=True,
        max_uses=0,
    )
    session.add(promo)
    await session.flush()
    return promo


async def create_admin_promo(
    session: AsyncSession,
    code: str,
    discount: int,
    description: str | None,
    max_uses: int = 0,
    expires_at: datetime | None = None,
    sponsor_only: bool = False,
    requires_active_subscription: bool = False,
) -> PromoCode:
    if not CODE_RE.match(code):
        raise PromoError("invalid code format")
    if discount < PROMO_DISCOUNT_MIN or discount > PROMO_DISCOUNT_MAX:
        raise PromoError("invalid discount")
    if await find_active(session, code):
        raise PromoError("code exists")
    promo = PromoCode(
        code=code,
        discount_percent=discount,
        description=description,
        creator_user_id=None,
        max_uses=max_uses,
        expires_at=expires_at,
        sponsor_only=sponsor_only,
        requires_active_subscription=requires_active_subscription,
        active=True,
    )
    session.add(promo)
    await session.flush()
    return promo
