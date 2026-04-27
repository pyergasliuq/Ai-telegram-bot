from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from db.models import User
from handlers.keyboards import (
    categories_kb,
    language_kb,
    main_menu_kb,
    mood_kb,
    plans_kb,
    settings_kb,
    speed_kb,
    stage_kb,
)
from services.channels import all_member, list_active
from services.users import current_plan, set_setting
from settings import PLAN_FEATURES, Mood, SpeedMode, StageMode

router = Router(name="callbacks")


@router.callback_query(F.data == "nav:main")
async def nav_main(cq: CallbackQuery, lang: str) -> None:
    await cq.message.answer(t(lang, "menu.main"), reply_markup=main_menu_kb(lang))
    await cq.answer()


@router.callback_query(F.data == "nav:billing")
async def nav_billing(cq: CallbackQuery, lang: str) -> None:
    await cq.message.edit_text(t(lang, "billing.choose_plan"), reply_markup=plans_kb(lang))
    await cq.answer()


@router.callback_query(F.data == "nav:settings")
async def nav_settings(cq: CallbackQuery, user: User, lang: str) -> None:
    plan = await current_plan(user)
    current = {
        "mood": (user.settings_data or {}).get("mood", Mood.SMART_FRIEND.value),
        "speed": (user.settings_data or {}).get("speed", SpeedMode.BALANCE.value),
        "stage": (user.settings_data or {}).get("stage", StageMode.ONE.value),
    }
    await cq.message.edit_text(t(lang, "settings.title"), reply_markup=settings_kb(lang, plan, current))
    await cq.answer()


@router.callback_query(F.data == "set:lang")
async def set_lang_open(cq: CallbackQuery, lang: str) -> None:
    await cq.message.edit_reply_markup(reply_markup=language_kb(lang))
    await cq.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_lang_apply(cq: CallbackQuery, session: AsyncSession, user: User) -> None:
    new = cq.data.split(":", 1)[1]
    if new not in ("ru", "en"):
        await cq.answer()
        return
    user.language = new
    await session.flush()
    await cq.message.answer(t(new, "settings.saved"), reply_markup=main_menu_kb(new))
    await cq.answer()


@router.callback_query(F.data == "set:mood")
async def set_mood_open(cq: CallbackQuery, user: User, lang: str) -> None:
    plan = await current_plan(user)
    await cq.message.edit_reply_markup(reply_markup=mood_kb(lang, plan))
    await cq.answer()


@router.callback_query(F.data.startswith("mood:"))
async def set_mood_apply(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    value = cq.data.split(":", 1)[1]
    plan = await current_plan(user)
    try:
        m = Mood(value)
    except ValueError:
        await cq.answer()
        return
    if m not in PLAN_FEATURES[plan]["moods"]:
        await cq.answer(t(lang, "settings.locked_for_plan"), show_alert=True)
        return
    set_setting(user, "mood", m.value)
    await session.flush()
    await cq.answer(t(lang, "settings.saved"))


@router.callback_query(F.data == "set:speed")
async def set_speed_open(cq: CallbackQuery, user: User, lang: str) -> None:
    plan = await current_plan(user)
    await cq.message.edit_reply_markup(reply_markup=speed_kb(lang, plan))
    await cq.answer()


@router.callback_query(F.data.startswith("speed:"))
async def set_speed_apply(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    value = cq.data.split(":", 1)[1]
    plan = await current_plan(user)
    try:
        s = SpeedMode(value)
    except ValueError:
        await cq.answer()
        return
    if s not in PLAN_FEATURES[plan]["speed_modes"]:
        await cq.answer(t(lang, "settings.locked_for_plan"), show_alert=True)
        return
    set_setting(user, "speed", s.value)
    await session.flush()
    await cq.answer(t(lang, "settings.saved"))


@router.callback_query(F.data == "set:stage")
async def set_stage_open(cq: CallbackQuery, user: User, lang: str) -> None:
    plan = await current_plan(user)
    await cq.message.edit_reply_markup(reply_markup=stage_kb(lang, plan))
    await cq.answer()


@router.callback_query(F.data.startswith("stage:"))
async def set_stage_apply(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    value = cq.data.split(":", 1)[1]
    plan = await current_plan(user)
    try:
        st = StageMode(value)
    except ValueError:
        await cq.answer()
        return
    if st not in PLAN_FEATURES[plan]["stages"]:
        await cq.answer(t(lang, "settings.locked_for_plan"), show_alert=True)
        return
    set_setting(user, "stage", st.value)
    await session.flush()
    await cq.answer(t(lang, "settings.saved"))


@router.callback_query(F.data == "channels:check")
async def channels_check(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    channels = await list_active(session)
    if not channels:
        user.channels_verified = True
        await session.flush()
        await cq.message.answer(t(lang, "channels.ok"), reply_markup=main_menu_kb(lang))
        await cq.answer()
        return
    ok, missing = await all_member(cq.bot, channels, cq.from_user.id)
    if ok:
        user.channels_verified = True
        await session.flush()
        await cq.message.answer(t(lang, "channels.ok"), reply_markup=main_menu_kb(lang))
    else:
        from handlers.keyboards import channels_kb

        pairs = [
            (c.channel_username.lstrip("@"), c.invite_link or f"https://t.me/{c.channel_username.lstrip('@')}")
            for c in missing
        ]
        await cq.message.answer(t(lang, "channels.not_subscribed"), reply_markup=channels_kb(lang, pairs))
    await cq.answer()


@router.callback_query(F.data.startswith("nav:back_categories"))
async def back_categories(cq: CallbackQuery, lang: str) -> None:
    await cq.message.edit_text(t(lang, "work.choose_category"), reply_markup=categories_kb(lang))
    await cq.answer()
