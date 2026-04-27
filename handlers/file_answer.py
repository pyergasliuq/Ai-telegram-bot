from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Document, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from core.pipeline import PipelineRequest
from core.pipeline import run as pipeline_run
from core.rate_limit import rate_limiter
from core.router import AllProvidersFailed
from db.models import User
from handlers.keyboards import file_format_kb
from handlers.states import FileAnswerStates
from services.files import (
    MAX_INPUT_BYTES,
    SUPPORTED_INPUT_EXT,
    FileError,
    ingest,
    render,
)
from services.users import consume_text, current_plan
from settings import (
    Mood,
    Plan,
    SpeedMode,
    StageMode,
    TaskPreset,
    TaskType,
)

log = logging.getLogger(__name__)
router = Router(name="file_answer")


@router.message(F.text.in_({"📎 Файл-ответ", "📎 File answer", "Файл-ответ", "File answer"}))
async def open_file_answer(message: Message, state: FSMContext, user: User, lang: str) -> None:
    plan = await current_plan(user)
    if plan == Plan.FREE:
        await message.answer(t(lang, "file.plus_only"))
        return
    await state.set_state(FileAnswerStates.waiting_question)
    await message.answer(t(lang, "file.choose_format"), reply_markup=file_format_kb(lang, "fafmt"))


@router.callback_query(F.data.startswith("fafmt:"))
async def file_format_chosen(cq: CallbackQuery, state: FSMContext, lang: str) -> None:
    fmt = cq.data.split(":", 1)[1]
    await state.update_data(file_answer_format=fmt)
    await cq.message.edit_text(t(lang, "file.send_question", fmt=fmt.upper()))
    await cq.answer()


@router.message(F.document)
async def handle_document(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    user: User,
    lang: str,
) -> None:
    plan = await current_plan(user)
    if plan == Plan.FREE:
        await message.answer(t(lang, "file.plus_only"))
        return
    doc: Document = message.document  # type: ignore[assignment]
    name = doc.file_name or "file"
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_INPUT_EXT:
        await message.answer(t(lang, "file.bad_format"))
        return
    if (doc.file_size or 0) > MAX_INPUT_BYTES:
        await message.answer(t(lang, "file.too_large"))
        return
    try:
        file_obj = await bot.get_file(doc.file_id)
        if not file_obj.file_path:
            await message.answer(t(lang, "file.read_failed"))
            return
        bio = await bot.download_file(file_obj.file_path)
        data = bio.read() if hasattr(bio, "read") else bytes(bio)
    except Exception as e:
        log.warning("download file failed: %s", e)
        await message.answer(t(lang, "file.read_failed"))
        return

    try:
        ingested = ingest(name, data)
    except FileError as e:
        log.info("ingest failed: %s", e)
        await message.answer(t(lang, "file.read_failed"))
        return

    caption = (message.caption or "").strip()
    if not caption:
        caption = t(lang, "file.default_question")
    user_message = f"{caption}\n\n=== {ingested.name} ===\n{ingested.text}"

    if not await consume_text(session, user):
        await message.answer(t(lang, "upsell.text_zero"))
        return
    placeholder = await message.answer(t(lang, "ai.thinking"))
    await rate_limiter.acquire_pending(user.telegram_id)
    try:
        req = PipelineRequest(
            user_message=user_message,
            plan=plan,
            language=lang,
            speed_mode=SpeedMode.BALANCE,
            stage_mode=StageMode.ONE,
            mood=Mood.SMART_FRIEND,
            task_preset=TaskPreset.DOCUMENTS,
            task_type=TaskType.TEXT_REASONING,
            history=[],
            summary_text="",
        )
        try:
            result = await pipeline_run(req)
        except AllProvidersFailed:
            await placeholder.edit_text(t(lang, "ai.failed"))
            return
        text = result.text
        try:
            await placeholder.edit_text(text[:4096])
        except Exception:
            await message.answer(text[:4096])
    finally:
        await rate_limiter.release_pending(user.telegram_id)


@router.message(FileAnswerStates.waiting_question, F.text & ~F.text.startswith("/"))
async def answer_in_file(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    lang: str,
) -> None:
    plan = await current_plan(user)
    if plan == Plan.FREE:
        await message.answer(t(lang, "file.plus_only"))
        await state.clear()
        return
    data = await state.get_data()
    fmt = (data.get("file_answer_format") or "md").lower()
    question = (message.text or "").strip()
    if len(question) < 3:
        await message.answer(t(lang, "file.question_too_short"))
        return
    if not await consume_text(session, user):
        await message.answer(t(lang, "upsell.text_zero"))
        await state.clear()
        return
    placeholder = await message.answer(t(lang, "ai.thinking"))
    await rate_limiter.acquire_pending(user.telegram_id)
    try:
        req = PipelineRequest(
            user_message=question,
            plan=plan,
            language=lang,
            speed_mode=SpeedMode.BALANCE,
            stage_mode=StageMode.ONE if plan in (Plan.PLUS, Plan.FREE) else StageMode.TWO,
            mood=Mood.SMART_FRIEND,
            task_preset=TaskPreset.DOCUMENTS,
            task_type=TaskType.TEXT_REASONING,
            history=[],
            summary_text="",
        )
        try:
            result = await pipeline_run(req)
        except AllProvidersFailed:
            await placeholder.edit_text(t(lang, "ai.failed"))
            return
        try:
            data_bytes, ext = render(result.text, fmt, title=question[:120])
        except FileError:
            data_bytes = result.text.encode("utf-8")
            ext = "txt"
        try:
            await placeholder.delete()
        except Exception:
            pass
        await message.answer_document(
            BufferedInputFile(data_bytes, filename=f"answer.{ext}"),
            caption=t(lang, "file.done"),
        )
    finally:
        await rate_limiter.release_pending(user.telegram_id)
        await state.clear()
