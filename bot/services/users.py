from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any

from aiogram.types import User as TgUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import PLAN_LIMITS, Plan
from bot.db.models import DailyQuota, Referral, User


def _gen_ref_code() -> str:
    return secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:10]


async def get_or_create(session: AsyncSession, tg: TgUser, ref_code: str | None = None) -> tuple[User, bool]:
    stmt = select(User).where(User.telegram_id == tg.id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    created = False
    if user is None:
        code = _gen_ref_code()
        while True:
            exists = (await session.execute(select(User).where(User.ref_code == code))).scalar_one_or_none()
            if not exists:
                break
            code = _gen_ref_code()
        user = User(
            telegram_id=tg.id,
            username=tg.username,
            full_name=tg.full_name,
            current_plan=Plan.FREE.value,
            ref_code=code,
            language="ru",
            settings_data={},
            trial_used_plans=[],
        )
        session.add(user)
        await session.flush()
        created = True
        if ref_code:
            await _attach_referral(session, user, ref_code)
    else:
        changed = False
        if user.username != tg.username:
            user.username = tg.username
            changed = True
        if user.full_name != tg.full_name:
            user.full_name = tg.full_name
            changed = True
        if changed:
            await session.flush()
    return user, created


async def _attach_referral(session: AsyncSession, invited: User, ref_code: str) -> None:
    inviter = (await session.execute(select(User).where(User.ref_code == ref_code))).scalar_one_or_none()
    if not inviter or inviter.id == invited.id:
        return
    invited.referred_by = inviter.telegram_id
    inviter.bonus_text_requests = (inviter.bonus_text_requests or 0) + 1
    session.add(
        Referral(
            inviter_user_id=inviter.telegram_id,
            invited_user_id=invited.telegram_id,
            reward_granted=True,
            reward_type="bonus_text_request",
        )
    )
    await session.flush()


async def current_plan(user: User) -> Plan:
    if user.subscription_expires_at and user.subscription_expires_at > datetime.utcnow():
        try:
            return Plan(user.current_plan)
        except ValueError:
            return Plan.FREE
    if user.current_plan != Plan.FREE.value:
        user.current_plan = Plan.FREE.value
    return Plan.FREE


async def get_or_init_quota(session: AsyncSession, user: User, today: date | None = None) -> DailyQuota:
    today = today or date.today()
    stmt = select(DailyQuota).where(DailyQuota.user_id == user.id, DailyQuota.date == today)
    q = (await session.execute(stmt)).scalar_one_or_none()
    plan = await current_plan(user)
    limits = PLAN_LIMITS[plan]
    if q is None:
        q = DailyQuota(
            user_id=user.id,
            date=today,
            text_used=0,
            text_limit=limits["text"],
            img_used=0,
            img_limit=limits["images"],
            voice_used=0,
            voice_limit=limits["tts"],
            stt_used=0,
            stt_limit=limits["stt"],
        )
        session.add(q)
        await session.flush()
    else:
        q.text_limit = limits["text"]
        q.img_limit = limits["images"]
        q.voice_limit = limits["tts"]
        q.stt_limit = limits["stt"]
    return q


async def consume_text(session: AsyncSession, user: User) -> bool:
    q = await get_or_init_quota(session, user)
    extra = user.bonus_text_requests or 0
    available = (q.text_limit - q.text_used) + extra
    if available <= 0:
        return False
    if q.text_used < q.text_limit:
        q.text_used += 1
    else:
        user.bonus_text_requests = max(0, extra - 1)
    await session.flush()
    return True


async def consume_image(session: AsyncSession, user: User) -> bool:
    q = await get_or_init_quota(session, user)
    if q.img_used >= q.img_limit:
        return False
    q.img_used += 1
    await session.flush()
    return True


async def consume_voice(session: AsyncSession, user: User) -> bool:
    q = await get_or_init_quota(session, user)
    if q.voice_used >= q.voice_limit:
        return False
    q.voice_used += 1
    await session.flush()
    return True


async def consume_stt(session: AsyncSession, user: User) -> bool:
    q = await get_or_init_quota(session, user)
    if q.stt_used >= q.stt_limit:
        return False
    q.stt_used += 1
    await session.flush()
    return True


async def referral_stats(session: AsyncSession, user: User) -> dict[str, int]:
    total = (
        await session.execute(
            select(func.count(Referral.id)).where(Referral.inviter_user_id == user.telegram_id)
        )
    ).scalar_one()
    paid = (
        await session.execute(
            select(func.count(Referral.id)).where(
                Referral.inviter_user_id == user.telegram_id,
                Referral.paid_user.is_(True),
            )
        )
    ).scalar_one()
    return {"total": int(total or 0), "paid": int(paid or 0)}


def settings_value(user: User, key: str, default: Any = None) -> Any:
    data = user.settings_data or {}
    return data.get(key, default)


def set_setting(user: User, key: str, value: Any) -> None:
    data = dict(user.settings_data or {})
    data[key] = value
    user.settings_data = data
