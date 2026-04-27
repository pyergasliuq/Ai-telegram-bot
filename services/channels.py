from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RequiredChannel

log = logging.getLogger(__name__)


async def list_active(session: AsyncSession) -> list[RequiredChannel]:
    stmt = select(RequiredChannel).where(RequiredChannel.active.is_(True))
    return list((await session.execute(stmt)).scalars().all())


async def is_member(bot: Bot, channel: RequiredChannel, user_id: int) -> bool:
    chat = channel.channel_username if channel.channel_username.startswith("@") else f"@{channel.channel_username}"
    if channel.channel_id:
        chat = channel.channel_id  # type: ignore[assignment]
    try:
        member = await bot.get_chat_member(chat_id=chat, user_id=user_id)
    except TelegramAPIError as e:
        log.warning("channel check failed for %s: %s", chat, e)
        return False
    return member.status in ("creator", "administrator", "member", "restricted")


async def all_member(bot: Bot, channels: list[RequiredChannel], user_id: int) -> tuple[bool, list[RequiredChannel]]:
    missing: list[RequiredChannel] = []
    for ch in channels:
        if not await is_member(bot, ch, user_id):
            missing.append(ch)
    return (not missing), missing
