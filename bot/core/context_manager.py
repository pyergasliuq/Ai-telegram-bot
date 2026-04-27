from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import Plan, SpeedMode, TaskType, settings
from bot.core.router import AllProvidersFailed, RouteContext, chat
from bot.db.models import ChatSession, Message
from bot.services.ai_providers.base import ChatMessage

log = logging.getLogger(__name__)


async def load_history(session: AsyncSession, chat_id: int, limit: int | None = None) -> list[Message]:
    n = limit if limit is not None else settings.KEEP_RECENT_MESSAGES
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(n)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(reversed(rows))


def to_chat_messages(rows: list[Message]) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for r in rows:
        if r.role in ("user", "assistant"):
            out.append(ChatMessage(role=r.role, content=r.content))
    return out


async def maybe_summarize(session: AsyncSession, chat: ChatSession, plan: Plan) -> None:
    total = await _message_count(session, chat.id)
    if total < settings.SUMMARIZE_EVERY_N_MESSAGES * 2:
        return
    if total % settings.SUMMARIZE_EVERY_N_MESSAGES != 0:
        return
    await summarize(session, chat, plan)


async def _message_count(session: AsyncSession, chat_id: int) -> int:
    from sqlalchemy import func as sa_func

    stmt = select(sa_func.count(Message.id)).where(Message.chat_id == chat_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def summarize(session: AsyncSession, chat_obj: ChatSession, plan: Plan) -> None:
    keep = settings.KEEP_RECENT_MESSAGES
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_obj.id)
        .order_by(Message.created_at.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    if len(rows) <= keep:
        return

    older = rows[:-keep]
    transcript_parts = [f"{m.role}: {m.content}" for m in older]
    prior_summary = (chat_obj.summary or {}).get("text", "")

    transcript = "\n".join(transcript_parts)[-12000:]
    sys_prompt = (
        "You compress chat history into a concise English summary suitable as system context. "
        "Keep: key topic, decisions, user preferences, open tasks, important facts. "
        "Be terse and structured. Output ONLY the summary."
    )
    user_prompt = (
        (f"Previous summary: {prior_summary}\n\n" if prior_summary else "")
        + f"New transcript to absorb:\n{transcript}"
    )

    messages = [
        ChatMessage(role="system", content=sys_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]
    ctx = RouteContext(plan=plan, task_type=TaskType.SUMMARIZER, speed_mode=SpeedMode.FAST, language="en")
    try:
        resp = await chat(ctx, messages, temperature=0.2, max_tokens=600)
        chat_obj.summary = {"text": resp.text}
        from sqlalchemy import delete

        ids_to_delete = [m.id for m in older]
        if ids_to_delete:
            await session.execute(delete(Message).where(Message.id.in_(ids_to_delete)))
        await session.flush()
    except AllProvidersFailed:
        log.warning("summarization failed, keeping full history")


async def maybe_update_title(session: AsyncSession, chat_obj: ChatSession, plan: Plan, last_user_message: str) -> None:
    if chat_obj.title and chat_obj.title not in ("Новый чат", "New chat"):
        return
    sys_prompt = (
        "Generate a 3-7 word chat title in the user's language based on the message. "
        "Output ONLY the title, no quotes."
    )
    messages = [
        ChatMessage(role="system", content=sys_prompt),
        ChatMessage(role="user", content=last_user_message[:1000]),
    ]
    ctx = RouteContext(plan=plan, task_type=TaskType.SUMMARIZER, speed_mode=SpeedMode.FAST, language="ru")
    try:
        resp = await chat(ctx, messages, temperature=0.4, max_tokens=40)
        title = resp.text.strip().strip('"').strip("«»").splitlines()[0]
        if title:
            chat_obj.title = title[:120]
            await session.flush()
    except AllProvidersFailed:
        return
