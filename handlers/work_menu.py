from __future__ import annotations

import logging
from io import BytesIO

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.context_manager import (
    load_history,
    maybe_summarize,
    maybe_update_title,
    to_chat_messages,
)
from core.i18n import t
from core.pipeline import PipelineRequest
from core.pipeline import run as pipeline_run
from core.rate_limit import rate_limiter
from core.router import AllProvidersFailed, RouteContext
from core.router import image as image_route
from db.models import ChatSession, User
from db.models import Message as DBMessage
from handlers.keyboards import categories_kb, chats_kb
from handlers.states import ChatStates
from services.users import (
    consume_image,
    consume_text,
    current_plan,
    get_or_init_quota,
)
from settings import (
    PLAN_FEATURES,
    PLAN_LIMITS,
    WORK_CATEGORIES,
    Mood,
    Plan,
    SpeedMode,
    StageMode,
    TaskPreset,
    TaskType,
)

log = logging.getLogger(__name__)
router = Router(name="work")


def _category(cat_id: str) -> dict | None:
    for c in WORK_CATEGORIES:
        if c["id"] == cat_id:
            return c
    return None


@router.callback_query(F.data == "nav:work")
async def back_to_work(cq: CallbackQuery, lang: str) -> None:
    await cq.message.edit_text(t(lang, "work.choose_category"), reply_markup=categories_kb(lang))
    await cq.answer()


@router.callback_query(F.data.startswith("cat:"))
async def open_category(cq: CallbackQuery, session: AsyncSession, user: User, lang: str) -> None:
    cat_id = cq.data.split(":", 1)[1]
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user.id, ChatSession.category == cat_id, ChatSession.archived.is_(False))
        .order_by(ChatSession.updated_at.desc())
        .limit(20)
    )
    rows = (await session.execute(stmt)).scalars().all()
    chats = [(c.id, c.title or t(lang, "work.new_chat")) for c in rows]
    title = t(lang, "work.chats_title") if chats else t(lang, "work.no_chats")
    await cq.message.edit_text(title, reply_markup=chats_kb(lang, cat_id, chats))
    await cq.answer()


@router.callback_query(F.data.startswith("chat:new:"))
async def new_chat(cq: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, lang: str) -> None:
    cat_id = cq.data.split(":", 2)[2]
    chat = ChatSession(
        user_id=user.id,
        category=cat_id,
        title=t(lang, "work.new_chat").lstrip("+ ").strip() or "Новый чат",
        summary={},
        meta={},
    )
    session.add(chat)
    await session.flush()
    await state.set_state(ChatStates.in_chat)
    await state.update_data(chat_id=chat.id, category=cat_id)
    await cq.message.answer(t(lang, "work.chat_created"))
    await cq.answer()


@router.callback_query(F.data.startswith("chat:open:"))
async def open_chat(cq: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str) -> None:
    chat_id = int(cq.data.split(":", 2)[2])
    chat = await session.get(ChatSession, chat_id)
    if not chat:
        await cq.answer()
        return
    await state.set_state(ChatStates.in_chat)
    await state.update_data(chat_id=chat.id, category=chat.category)
    await cq.message.answer(t(lang, "work.in_chat_hint", title=chat.title))
    await cq.answer()


@router.message(ChatStates.in_chat, F.text & ~F.text.startswith("/"))
async def chat_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    lang: str,
) -> None:
    plan = await current_plan(user)
    text = (message.text or "").strip()
    if len(text) > PLAN_LIMITS[plan]["max_message_chars"]:
        await message.answer(t(lang, "antispam.message_too_long"))
        return

    ok, err = await rate_limiter.check_message(user.telegram_id, plan)
    if not ok:
        await message.answer(t(lang, err or "antispam.too_fast"))
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")
    cat_id = data.get("category")
    if not chat_id or not cat_id:
        await message.answer(t(lang, "common.unknown_command"))
        return

    cat = _category(cat_id)
    if cat is None:
        await message.answer(t(lang, "common.unknown_command"))
        return
    task_preset: TaskPreset = cat["task_preset"]
    task_type: TaskType = cat["task_type"]

    if task_type == TaskType.IMAGE:
        await _handle_image(message, session, user, lang, plan, prompt=text)
        return

    if not await consume_text(session, user):
        await message.answer(t(lang, "upsell.text_zero"))
        return

    chat_obj = await session.get(ChatSession, chat_id)
    if not chat_obj:
        await message.answer(t(lang, "common.unknown_command"))
        return

    history_rows = await load_history(session, chat_obj.id)
    history = to_chat_messages(history_rows)
    summary_text = (chat_obj.summary or {}).get("text", "")

    s = user.settings_data or {}
    mood = Mood(s.get("mood", Mood.SMART_FRIEND.value))
    speed = SpeedMode(s.get("speed", SpeedMode.BALANCE.value))
    stage = StageMode(s.get("stage", StageMode.ONE.value))
    if speed not in PLAN_FEATURES[plan]["speed_modes"]:
        speed = PLAN_FEATURES[plan]["speed_modes"][0]
    if stage not in PLAN_FEATURES[plan]["stages"]:
        stage = PLAN_FEATURES[plan]["stages"][0]
    if mood not in PLAN_FEATURES[plan]["moods"]:
        mood = PLAN_FEATURES[plan]["moods"][0]

    thinking_key = "ai.thinking"
    if stage in (StageMode.TWO, StageMode.THREE):
        thinking_key = "ai.searching"
    placeholder = await message.answer(t(lang, thinking_key))

    await rate_limiter.acquire_pending(user.telegram_id)
    try:
        req = PipelineRequest(
            user_message=text,
            plan=plan,
            language=lang,
            speed_mode=speed,
            stage_mode=stage,
            mood=mood,
            task_preset=task_preset,
            task_type=task_type,
            history=history,
            summary_text=summary_text,
        )
        try:
            result = await pipeline_run(req)
        except AllProvidersFailed:
            await placeholder.edit_text(t(lang, "ai.failed"))
            return

        session.add(
            DBMessage(
                chat_id=chat_obj.id,
                role="user",
                content=text,
                provider=None,
                model=None,
            )
        )
        session.add(
            DBMessage(
                chat_id=chat_obj.id,
                role="assistant",
                content=result.text,
                provider=result.provider,
                model=result.model,
            )
        )
        await session.flush()

        try:
            await placeholder.edit_text(result.text[:4096])
        except Exception:
            await message.answer(result.text[:4096])

        await maybe_summarize(session, chat_obj, plan)
        await maybe_update_title(session, chat_obj, plan, text)
    finally:
        await rate_limiter.release_pending(user.telegram_id)


async def _handle_image(
    message: Message,
    session: AsyncSession,
    user: User,
    lang: str,
    plan: Plan,
    prompt: str,
) -> None:
    quota = await get_or_init_quota(session, user)
    remaining_after = quota.img_limit - quota.img_used - 1
    if remaining_after < -1:
        return
    if not await consume_image(session, user):
        await message.answer(t(lang, "upsell.image_zero"))
        return
    placeholder = await message.answer(t(lang, "ai.image_generating"))
    try:
        ctx = RouteContext(plan=plan, task_type=TaskType.IMAGE, speed_mode=SpeedMode.BALANCE, language=lang)
        try:
            resp = await image_route(ctx, prompt=prompt)
        except AllProvidersFailed:
            await placeholder.edit_text(t(lang, "ai.image_failed"))
            return
        if not resp.images:
            await placeholder.edit_text(t(lang, "ai.image_failed"))
            return
        bio = BytesIO(resp.images[0])
        bio.seek(0)
        await message.answer_photo(BufferedInputFile(bio.read(), filename="image.png"))
        try:
            await placeholder.delete()
        except Exception:
            pass
        if plan == Plan.FREE and remaining_after == 0:
            await message.answer(t(lang, "upsell.image_one_left"))
        elif plan == Plan.FREE and remaining_after < 0:
            await message.answer(t(lang, "upsell.image_zero"))
    except Exception:
        log.exception("image generation failed")
        await placeholder.edit_text(t(lang, "ai.image_failed"))


@router.message(ChatStates.in_chat, F.photo)
async def reject_unsupported(message: Message, lang: str) -> None:
    await message.answer(t(lang, "common.unknown_command"))
