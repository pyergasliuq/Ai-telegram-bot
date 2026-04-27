from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.i18n import t
from bot.db.models import User
from bot.handlers.states import ReferralPromoStates
from bot.services.promo import (
    PromoError,
    can_create_user_promo,
    create_user_promo,
)
from bot.services.users import referral_stats

router = Router(name="referrals")


def _ref_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start={code}"


@router.message(F.text.in_({"Реферальная программа", "Referral program"}))
async def open_referrals(message: Message, session: AsyncSession, user: User, lang: str) -> None:
    me = await message.bot.get_me()
    link = _ref_link(me.username or "", user.ref_code)
    stats = await referral_stats(session, user)
    paid = stats["paid"]
    text = "\n".join(
        [
            t(lang, "referral.title"),
            t(lang, "referral.your_link", link=link),
            t(lang, "referral.stats", total=stats["total"], paid=paid),
            t(lang, "referral.reward_info"),
        ]
    )
    rows: list[list[InlineKeyboardButton]] = []
    if await can_create_user_promo(session, user):
        text += "\n\n" + t(lang, "referral.unlock_promo", paid=paid)
        rows.append(
            [InlineKeyboardButton(text=t(lang, "referral.create_promo_btn"), callback_data="ref:create_promo")]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "ref:create_promo")
async def create_promo_prompt(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(ReferralPromoStates.waiting_create)
    await cq.message.answer(t(lang, "referral.promo_prompt"))
    await cq.answer()


@router.message(ReferralPromoStates.waiting_create)
async def create_promo_run(message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(t(lang, "referral.promo_invalid"))
        await state.clear()
        return
    code = parts[0]
    discount = int(parts[1])
    try:
        promo = await create_user_promo(session, user, code, discount)
    except PromoError:
        await message.answer(t(lang, "referral.promo_invalid"))
        await state.clear()
        return
    await message.answer(t(lang, "referral.promo_created", code=promo.code, discount=promo.discount_percent))
    await state.clear()
