from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config.settings import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs() -> dict[str, object]:
    url = settings.DATABASE_URL
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        return kwargs
    kwargs["pool_size"] = settings.DB_POOL_SIZE
    kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE_S
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
