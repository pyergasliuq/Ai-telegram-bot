from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timedelta
from functools import wraps

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from db.models import (
    BroadcastJob,
    Payment,
    PromoCode,
    ProviderStatus,
    RequiredChannel,
    Subscription,
    User,
)
from db.models import (
    Message as DBMessage,
)
from handlers.keyboards import admin_menu_kb
from handlers.states import AdminStates
from services.promo import PromoError, create_admin_promo
from settings import Plan, settings

log = logging.getLogger(__name__)
router = Router(name="admin")

_BACKGROUND_TASKS: set[asyncio.Task] = set()


def is_admin(tg_id: int) -> bool:
    return tg_id in settings.ADMIN_IDS


def _admin_only(handler):
    sig = inspect.signature(handler)
    params = list(sig.parameters.values())
    has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    allowed = {
        p.name
        for p in params[1:]
        if p.kind
        in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    }

    @wraps(handler)
    async def _wrap(event, **kwargs):
        from_user = getattr(event, "from_user", None)
        if not from_user or not is_admin(from_user.id):
            lang = kwargs.get("lang", "ru")
            if isinstance(event, Message):
                await event.answer(t(lang, "admin.no_access"))
            elif isinstance(event, CallbackQuery):
                await event.answer(t(lang, "admin.no_access"), show_alert=True)
            return None
        if has_kwargs:
            return await handler(event, **kwargs)
        return await handler(event, **{k: v for k, v in kwargs.items() if k in allowed})

    return _wrap


@router.message(Command("admin"))
@_admin_only
async def admin_root(message: Message, lang: str) -> None:
    await message.answer(t(lang, "admin.menu"), reply_markup=admin_menu_kb(lang))


@router.callback_query(F.data == "admin:stats")
@_admin_only
async def admin_stats(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
    active_subs = (
        await session.execute(
            select(func.count(Subscription.id)).where(Subscription.expires_at > datetime.utcnow())
        )
    ).scalar_one()
    plan_counts = {}
    for plan in Plan:
        cnt = (
            await session.execute(
                select(func.count(User.id)).where(
                    User.current_plan == plan.value,
                    User.subscription_expires_at > datetime.utcnow(),
                )
            )
            if plan != Plan.FREE
            else session.execute(
                select(func.count(User.id)).where(User.current_plan == plan.value)
            )
        ).scalar_one()
        plan_counts[plan.value] = int(cnt or 0)
    one_day = datetime.utcnow() - timedelta(days=1)
    msgs_24h = (
        await session.execute(select(func.count(DBMessage.id)).where(DBMessage.created_at >= one_day))
    ).scalar_one()
    paid_24h = (
        await session.execute(
            select(func.count(Payment.id)).where(
                Payment.status == "paid", Payment.created_at >= one_day
            )
        )
    ).scalar_one()
    lines = [
        f"Total users: {total_users}",
        f"Active subscriptions: {active_subs}",
        *(f"  {p}: {c}" for p, c in plan_counts.items()),
        f"Messages 24h: {msgs_24h}",
        f"Paid 24h: {paid_24h}",
    ]
    await cq.message.answer("\n".join(lines), reply_markup=admin_menu_kb(lang))
    await cq.answer()


@router.callback_query(F.data == "admin:broadcast")
@_admin_only
async def admin_broadcast_prompt(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(AdminStates.waiting_broadcast)
    await cq.message.answer(t(lang, "admin.broadcast_prompt"))
    await cq.answer()


@router.message(AdminStates.waiting_broadcast)
@_admin_only
async def admin_broadcast_run(message: Message, state: FSMContext, session: AsyncSession, lang: str, user: User) -> None:
    text = message.text or ""
    if not text:
        await state.clear()
        return
    job = BroadcastJob(admin_id=user.telegram_id, text=text, status="running")
    session.add(job)
    await session.flush()
    await state.clear()
    await message.answer(t(lang, "admin.broadcast_started"))
    task = asyncio.create_task(_run_broadcast(message.bot, job.id, text))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def _run_broadcast(bot: Bot, job_id: int, text: str) -> None:
    from db.session import async_session_maker

    async with async_session_maker() as session:
        rows = (await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))).all()
        ids = [r[0] for r in rows]
        sent = 0
        failed = 0
        for tg_id in ids:
            try:
                await bot.send_message(tg_id, text)
                sent += 1
            except TelegramAPIError:
                failed += 1
            await asyncio.sleep(0.04)
        job = await session.get(BroadcastJob, job_id)
        if job:
            job.sent = sent
            job.failed = failed
            job.status = "done"
        await session.commit()


@router.callback_query(F.data == "admin:users")
@_admin_only
async def admin_users_prompt(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(AdminStates.waiting_user_lookup)
    await cq.message.answer(t(lang, "admin.user_lookup"))
    await cq.answer()


@router.message(AdminStates.waiting_user_lookup)
@_admin_only
async def admin_users_run(message: Message, state: FSMContext, session: AsyncSession, lang: str, user: User) -> None:
    text = (message.text or "").strip()
    await state.clear()
    if not text.lstrip("-").isdigit():
        await message.answer(t(lang, "admin.user_not_found"))
        return
    target = (await session.execute(select(User).where(User.telegram_id == int(text)))).scalar_one_or_none()
    if not target:
        await message.answer(t(lang, "admin.user_not_found"))
        return
    expires = target.subscription_expires_at.strftime("%Y-%m-%d") if target.subscription_expires_at else "—"
    info = (
        f"id: {target.telegram_id}\n"
        f"username: @{target.username or '-'}\n"
        f"plan: {target.current_plan}\n"
        f"expires: {expires}\n"
        f"banned: {target.is_banned} muted: {target.is_muted}\n"
        f"language: {target.language}"
    )
    rows = [
        [
            InlineKeyboardButton(text="Ban" if not target.is_banned else "Unban", callback_data=f"adm:ban:{target.telegram_id}"),
            InlineKeyboardButton(text="Mute" if not target.is_muted else "Unmute", callback_data=f"adm:mute:{target.telegram_id}"),
        ],
        [
            InlineKeyboardButton(text="+30d Plus", callback_data=f"adm:grant:{target.telegram_id}:plus:30"),
            InlineKeyboardButton(text="+30d Pro", callback_data=f"adm:grant:{target.telegram_id}:pro:30"),
            InlineKeyboardButton(text="+30d Max", callback_data=f"adm:grant:{target.telegram_id}:max:30"),
        ],
        [InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")],
    ]
    await message.answer(info, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("adm:ban:"))
@_admin_only
async def admin_toggle_ban(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    tg_id = int(cq.data.split(":")[2])
    target = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
    if target:
        target.is_banned = not target.is_banned
        await session.flush()
    await cq.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data.startswith("adm:mute:"))
@_admin_only
async def admin_toggle_mute(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    tg_id = int(cq.data.split(":")[2])
    target = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
    if target:
        target.is_muted = not target.is_muted
        await session.flush()
    await cq.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data.startswith("adm:grant:"))
@_admin_only
async def admin_grant(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    parts = cq.data.split(":")
    tg_id = int(parts[2])
    plan_str = parts[3]
    days = int(parts[4])
    target = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
    if not target:
        await cq.answer(t(lang, "admin.user_not_found"))
        return
    from services.payments import activate_subscription

    plan = Plan(plan_str)
    await activate_subscription(session, target, plan, days, "manual")
    await cq.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data == "admin:channels")
@_admin_only
async def admin_channels(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    rows = (await session.execute(select(RequiredChannel))).scalars().all()
    text_lines = ["Required channels:"]
    kb_rows: list[list[InlineKeyboardButton]] = []
    for ch in rows:
        text_lines.append(f"{'on ' if ch.active else 'off'} @{ch.channel_username}")
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=("Off " if ch.active else "On ") + ch.channel_username,
                    callback_data=f"adm:chtoggle:{ch.id}",
                ),
                InlineKeyboardButton(text="Del", callback_data=f"adm:chdel:{ch.id}"),
            ]
        )
    kb_rows.append([InlineKeyboardButton(text="+ Add", callback_data="adm:chadd")])
    kb_rows.append([InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")])
    await cq.message.answer("\n".join(text_lines) or "—", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cq.answer()


@router.callback_query(F.data == "adm:chadd")
@_admin_only
async def admin_chadd(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(AdminStates.waiting_channel_add)
    await cq.message.answer("Send: @username https://t.me/+invite_or_optional")
    await cq.answer()


@router.message(AdminStates.waiting_channel_add)
@_admin_only
async def admin_chadd_run(message: Message, state: FSMContext, session: AsyncSession, lang: str, user: User) -> None:
    parts = (message.text or "").split()
    await state.clear()
    if not parts:
        return
    username = parts[0].lstrip("@")
    link = parts[1] if len(parts) > 1 else f"https://t.me/{username}"
    session.add(RequiredChannel(channel_username=username, invite_link=link, active=True, title=username))
    await session.flush()
    await message.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data.startswith("adm:chtoggle:"))
@_admin_only
async def admin_chtoggle(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    cid = int(cq.data.split(":")[2])
    ch = await session.get(RequiredChannel, cid)
    if ch:
        ch.active = not ch.active
        await session.flush()
    await cq.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data.startswith("adm:chdel:"))
@_admin_only
async def admin_chdel(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    cid = int(cq.data.split(":")[2])
    ch = await session.get(RequiredChannel, cid)
    if ch:
        await session.delete(ch)
        await session.flush()
    await cq.answer(t(lang, "admin.action_done"))


@router.callback_query(F.data == "admin:providers")
@_admin_only
async def admin_providers(cq: CallbackQuery, session: AsyncSession, lang: str) -> None:
    rows = (await session.execute(select(ProviderStatus).order_by(ProviderStatus.provider_name))).scalars().all()
    if not rows:
        await cq.message.answer("No tracked providers yet.", reply_markup=admin_menu_kb(lang))
        await cq.answer()
        return
    lines = []
    for r in rows:
        cd = r.cooldown_until.strftime("%H:%M:%S") if r.cooldown_until else "—"
        lines.append(f"{'on' if r.active else 'off'} {r.provider_name}/{r.model} fails={r.fail_count} cd={cd}")
    await cq.message.answer("\n".join(lines), reply_markup=admin_menu_kb(lang))
    await cq.answer()


@router.callback_query(F.data == "admin:promos")
@_admin_only
async def admin_promos(cq: CallbackQuery, state: FSMContext, lang: str, session: AsyncSession) -> None:
    rows = (await session.execute(select(PromoCode).order_by(PromoCode.created_at.desc()).limit(20))).scalars().all()
    text_lines = ["Recent promos:"]
    for p in rows:
        text_lines.append(f"{p.code} -{p.discount_percent}% used={p.used_count}/{p.max_uses or '∞'} active={p.active}")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="+ Create", callback_data="adm:promonew")],
            [InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")],
        ]
    )
    await cq.message.answer("\n".join(text_lines), reply_markup=kb)
    await cq.answer()


@router.callback_query(F.data == "adm:promonew")
@_admin_only
async def admin_promonew(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(AdminStates.waiting_promo_create)
    await cq.message.answer("Send: <code> <discount 5-20> [max_uses] [days_valid]")
    await cq.answer()


@router.message(AdminStates.waiting_promo_create)
@_admin_only
async def admin_promonew_run(message: Message, state: FSMContext, session: AsyncSession, lang: str, user: User) -> None:
    parts = (message.text or "").split()
    await state.clear()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(t(lang, "referral.promo_invalid"))
        return
    code = parts[0]
    discount = int(parts[1])
    max_uses = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    days_valid = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    expires = (datetime.utcnow() + timedelta(days=days_valid)) if days_valid else None
    try:
        promo = await create_admin_promo(session, code, discount, None, max_uses, expires)
    except PromoError:
        await message.answer(t(lang, "referral.promo_invalid"))
        return
    await message.answer(t(lang, "referral.promo_created", code=promo.code, discount=promo.discount_percent))
