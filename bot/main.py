from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.background import poll_crypto_invoices
from bot.config.settings import settings, shared_path
from bot.handlers import build_root_router
from bot.handlers.deps import DBSessionMiddleware, UserMiddleware
from bot.services.payments import crypto_bot


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
    dp = Dispatcher(storage=MemoryStorage())
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
