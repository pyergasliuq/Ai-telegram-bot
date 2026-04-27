from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from background import poll_crypto_invoices
from core.fsm_storage import SQLAlchemyStorage
from db.session import async_session_maker, init_db
from handlers import build_root_router
from handlers.deps import DBSessionMiddleware, UserMiddleware
from services.payments import crypto_bot
from settings import settings, shared_path


def _setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_file = shared_path("logs", "bot.log")
        handlers.append(RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)


async def _build_dp() -> Dispatcher:
    dp = Dispatcher(storage=SQLAlchemyStorage(async_session_maker))
    db_mw = DBSessionMiddleware()
    user_mw = UserMiddleware()

    dp.message.middleware(db_mw)
    dp.callback_query.middleware(db_mw)
    dp.pre_checkout_query.middleware(db_mw)

    dp.message.middleware(user_mw)
    dp.callback_query.middleware(user_mw)
    dp.pre_checkout_query.middleware(user_mw)

    dp.include_router(build_root_router())
    return dp


async def main() -> None:
    _setup_logging()
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    await init_db()

    bot = Bot(
        settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = await _build_dp()

    poller = asyncio.create_task(poll_crypto_invoices())
    try:
        await dp.start_polling(bot)
    finally:
        poller.cancel()
        try:
            await poller
        except asyncio.CancelledError:
            pass
        await crypto_bot.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
