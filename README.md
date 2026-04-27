# Ai-telegram-bot

Multi-provider AI Telegram platform built on aiogram 3.x with subscription tiers (Free / Plus / Pro / Max), multi-stage reasoning, smart context compression, admin panel, referrals, promo codes, Stars + Crypto Bot payments and Russian-by-default UX.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env

alembic upgrade head

python -m bot.main
```

## Configuration

All providers, models, plans, prices and limits live in `bot/config/settings.py`. Provider keys are optional — missing keys cause the router to skip that provider automatically.

## Project layout

```
bot/
  core/        router, pipeline, context_manager, rate_limit, i18n
  config/      settings.py (single source of truth)
  db/          SQLAlchemy models + Alembic migrations
  handlers/    aiogram routers
  services/    payments, promo, channels, crypto rates
    ai_providers/  per-provider HTTP clients
  locale/      ru/, en/ JSON message catalogues
  main.py
```

## Admin

Default admin Telegram ID is `2080411409`. Add more via `ADMIN_IDS` (comma separated).

## Payments

- Telegram Stars (native invoices).
- Crypto Bot (TON / USDT / BTC) via `CRYPTO_BOT_TOKEN`.
- Manual: `@keedboy016`.

USD is the base currency, crypto equivalents are computed live from CoinGecko with caching.
