from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from db.models import User
from handlers.states import PromoStates
from services.promo import PromoError, already_used, check_user_eligible, find_active
from services.users import current_plan, referral_stats

router = Router(name="account")


@router.message(F.text.in_({"Аккаунт", "Account"}))
async def open_account(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    plan = await current_plan(user)
    stats = await referral_stats(session, user)
    expires = (
        user.subscription_expires_at.strftime("%Y-%m-%d %H:%M")
        if user.subscription_expires_at
        else t(lang, "account.no_subscription")
    )
    lines = [
        t(lang, "account.title"),
        f"{t(lang, 'account.plan')}: {t(lang, f'plan.{plan.value}')}",
        f"{t(lang, 'account.expires')}: {expires}",
        f"{t(lang, 'account.lang')}: {user.language.upper()}",
        f"{t(lang, 'account.referrals')}: {stats['total']}",
        f"{t(lang, 'account.paid_referrals')}: {stats['paid']}",
        f"{t(lang, 'account.bonus_text')}: {user.bonus_text_requests or 0}",
    ]
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "account.enter_promo"), callback_data="promo:enter")],
            [InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")],
        ]
    )
    await message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data == "promo:enter")
async def promo_enter(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(PromoStates.waiting_code)
    await cq.message.answer(t(lang, "account.promo_prompt"))
    await cq.answer()


@router.message(PromoStates.waiting_code)
async def promo_apply(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    code = (message.text or "").strip()
    promo = await find_active(session, code)
    if not promo:
        await message.answer(t(lang, "account.promo_invalid"))
        await state.clear()
        return
    if await already_used(session, promo.id, user.telegram_id):
        await message.answer(t(lang, "account.promo_used"))
        await state.clear()
        return
    try:
        check_user_eligible(promo, user)
    except PromoError:
        await message.answer(t(lang, "account.promo_invalid"))
        await state.clear()
        return
    user_data = dict(user.settings_data or {})
    user_data["pending_promo"] = code
    user.settings_data = user_data
    await session.flush()
    await message.answer(t(lang, "account.promo_ok", discount=promo.discount_percent))
    await state.clear()


@router.message(Command("language"))
async def quick_language(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    new = "en" if user.language == "ru" else "ru"
    user.language = new
    await session.flush()
    await message.answer(t(new, "settings.saved"))
