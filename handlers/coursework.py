from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.coursework import run_coursework
from core.i18n import t
from core.rate_limit import rate_limiter
from core.router import AllProvidersFailed
from db.models import User
from handlers.keyboards import file_format_kb
from handlers.states import CourseworkStates
from services.files import FileError, render
from services.users import consume_coursework, current_plan
from settings import Plan

log = logging.getLogger(__name__)
router = Router(name="coursework")


@router.message(F.text.in_({"Курсовая", "Coursework", "📚 Курсовая", "📚 Coursework"}))
async def open_coursework(
    message: Message,
    state: FSMContext,
    user: User,
    lang: str,
) -> None:
    plan = await current_plan(user)
    if plan != Plan.MAX:
        await message.answer(t(lang, "coursework.max_only"))
        return
    await state.set_state(CourseworkStates.waiting_topic)
    await message.answer(t(lang, "coursework.choose_format"), reply_markup=file_format_kb(lang, "cwfmt"))


@router.callback_query(F.data.startswith("cwfmt:"))
async def select_format(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    fmt = cq.data.split(":", 1)[1]
    await state.update_data(coursework_format=fmt)
    await cq.message.edit_text(t(lang, "coursework.send_topic", fmt=fmt.upper()))
    await cq.answer()


@router.message(CourseworkStates.waiting_topic, F.text & ~F.text.startswith("/"))
async def run_pipeline(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    lang: str,
) -> None:
    plan = await current_plan(user)
    if plan != Plan.MAX:
        await message.answer(t(lang, "coursework.max_only"))
        await state.clear()
        return
    data = await state.get_data()
    fmt = (data.get("coursework_format") or "docx").lower()
    topic = (message.text or "").strip()
    if len(topic) < 3:
        await message.answer(t(lang, "coursework.topic_too_short"))
        return
    if not await consume_coursework(session, user):
        await message.answer(t(lang, "coursework.no_quota"))
        await state.clear()
        return

    placeholder = await message.answer(t(lang, "coursework.running"))
    await rate_limiter.acquire_pending(user.telegram_id)
    try:
        try:
            result = await run_coursework(topic=topic, language=lang, plan=plan)
        except AllProvidersFailed:
            await placeholder.edit_text(t(lang, "ai.failed"))
            await state.clear()
            return
        try:
            data_bytes, ext = render(result.text, fmt, title=topic[:120])
        except FileError as e:
            log.warning("coursework render failed: %s", e)
            data_bytes = result.text.encode("utf-8")
            ext = "txt"
        filename = f"coursework.{ext}"
        await message.answer_document(
            BufferedInputFile(data_bytes, filename=filename),
            caption=t(lang, "coursework.done"),
        )
        try:
            await placeholder.delete()
        except Exception:
            pass
    finally:
        await rate_limiter.release_pending(user.telegram_id)
        await state.clear()
