from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from db.models import User
from handlers.admin import is_admin
from handlers.keyboards import admin_menu_kb, main_menu_kb
from services.channels import all_member, list_active
from services.users import current_plan, get_or_init_quota
from settings import Plan

router = Router(name="main_menu")


def _plan_name(lang: str, plan: Plan) -> str:
    return t(lang, f"plan.{plan.value}")


async def _send_main(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    plan = await current_plan(user)
    quota = await get_or_init_quota(session, user)
    text = t(
        lang,
        "welcome",
        username=user.full_name or user.username or "",
        plan_name=_plan_name(lang, plan),
        text_left=max(0, quota.text_limit - quota.text_used) + (user.bonus_text_requests or 0),
        img_left=max(0, quota.img_limit - quota.img_used),
        voice_left=max(0, quota.voice_limit - quota.voice_used),
    )
    await message.answer(
        text,
        reply_markup=main_menu_kb(lang, is_admin=is_admin(user.telegram_id)),
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_ref(message: Message, command, session: AsyncSession, user: User, lang: str) -> None:  # type: ignore[no-untyped-def]
    payload = (command.args or "").strip()
    ref_code = payload if payload else None
    if ref_code and not user.referred_by:
        from services.users import _attach_referral

        await _attach_referral(session, user, ref_code)
    await _enforce_channels(message, session, user, lang)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    await _enforce_channels(message, session, user, lang)


async def _enforce_channels(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    plan = await current_plan(user)
    if plan == Plan.FREE and not user.channels_verified:
        channels = await list_active(session)
        if channels:
            ok, missing = await all_member(message.bot, channels, user.from_user.id if message.from_user else user.telegram_id)
            if not ok:
                from handlers.keyboards import channels_kb

                pairs = [
                    (c.channel_username.lstrip("@"), c.invite_link or f"https://t.me/{c.channel_username.lstrip('@')}")
                    for c in missing
                ]
                await message.answer(
                    t(lang, "channels.required_title"),
                    reply_markup=channels_kb(lang, pairs),
                )
                return
            user.channels_verified = True
            await session.flush()
    await _send_main(message, session, user, lang)


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    await _send_main(message, session, user, lang)


@router.message(F.text.in_({"Начать работу", "Start working"}))
async def open_work(message: Message, lang: str) -> None:
    from handlers.keyboards import categories_kb

    await message.answer(t(lang, "work.choose_category"), reply_markup=categories_kb(lang))


@router.message(F.text.in_({"Помощь / FAQ", "Help / FAQ"}))
async def help_text(message: Message, lang: str) -> None:
    await message.answer(t(lang, "help.text"))


@router.message(F.text.in_({"Админ", "Admin", "🛠 Админ", "🛠 Admin"}))
async def open_admin_panel(message: Message, user: User, lang: str) -> None:
    if not is_admin(user.telegram_id):
        return
    await message.answer(t(lang, "admin.menu"), reply_markup=admin_menu_kb(lang))


@router.message(F.text.in_({"Настройки", "Settings"}))
async def settings_open(message: Message, user: User, lang: str) -> None:
    from handlers.keyboards import settings_kb

    plan = await current_plan(user)
    current = {
        "mood": (user.settings_data or {}).get("mood", "smart_friend"),
        "speed": (user.settings_data or {}).get("speed", "balance"),
        "stage": (user.settings_data or {}).get("stage", "one"),
    }
    await message.answer(t(lang, "settings.title"), reply_markup=settings_kb(lang, plan, current))
