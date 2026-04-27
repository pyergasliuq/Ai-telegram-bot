from __future__ import annotations

from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models import FSMState


class SQLAlchemyStorage(BaseStorage):
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._sm = session_maker

    async def _get_or_create(self, key: StorageKey, session: Any) -> FSMState:
        stmt = select(FSMState).where(
            FSMState.bot_id == key.bot_id,
            FSMState.chat_id == key.chat_id,
            FSMState.user_id == key.user_id,
            FSMState.thread_id == key.thread_id,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = FSMState(
                bot_id=key.bot_id,
                chat_id=key.chat_id,
                user_id=key.user_id,
                thread_id=key.thread_id,
                state=None,
                data={},
            )
            session.add(row)
            await session.flush()
        return row

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        value = state.state if isinstance(state, State) else state
        async with self._sm() as session:
            row = await self._get_or_create(key, session)
            row.state = value
            await session.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self._sm() as session:
            stmt = select(FSMState.state).where(
                FSMState.bot_id == key.bot_id,
                FSMState.chat_id == key.chat_id,
                FSMState.user_id == key.user_id,
                FSMState.thread_id == key.thread_id,
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        async with self._sm() as session:
            row = await self._get_or_create(key, session)
            row.data = dict(data)
            await session.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self._sm() as session:
            stmt = select(FSMState.data).where(
                FSMState.bot_id == key.bot_id,
                FSMState.chat_id == key.chat_id,
                FSMState.user_id == key.user_id,
                FSMState.thread_id == key.thread_id,
            )
            data = (await session.execute(stmt)).scalar_one_or_none()
            return dict(data) if data else {}

    async def update_data(self, key: StorageKey, data: dict[str, Any]) -> dict[str, Any]:
        async with self._sm() as session:
            row = await self._get_or_create(key, session)
            merged = dict(row.data or {})
            merged.update(data)
            row.data = merged
            await session.commit()
            return merged

    async def close(self) -> None:
        return None

    async def clear(self, key: StorageKey) -> None:
        async with self._sm() as session:
            await session.execute(
                delete(FSMState).where(
                    FSMState.bot_id == key.bot_id,
                    FSMState.chat_id == key.chat_id,
                    FSMState.user_id == key.user_id,
                    FSMState.thread_id == key.thread_id,
                )
            )
            await session.commit()
