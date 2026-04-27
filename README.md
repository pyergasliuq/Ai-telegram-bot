# Ai-telegram-bot

Multi-provider AI Telegram platform built on aiogram 3.x with subscription tiers (Free / Plus / Pro / Max), multi-stage reasoning, smart context compression, admin panel, referrals, promo codes, Stars + Crypto Bot payments and Russian-by-default UX. Designed to deploy on **Bothost.ru** (PaaS) using long polling, remote PostgreSQL and the shared `/app/shared` volume for persistent logs.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env

alembic upgrade head

python main.py
```

The entry point is `main.py` at the repo root (Bothost convention). It re-exports `bot.main:main`. Long polling is the only supported transport — webhooks are intentionally not wired.

## Configuration

All providers, models, plans, prices and limits live in `bot/config/settings.py`. Provider keys are optional — missing keys cause the router to skip that provider automatically.

### Provider tiers

Providers are tagged `tier: "free" | "paid"` in `PROVIDERS`:

- **Free tier** (Free/Plus/Pro/Max all see it): Google AI Studio, Groq, OpenRouter, OnlySQ, Together, Cerebras, SambaNova, Cloudflare, Hugging Face, Fireworks.
- **Paid tier** (Pro/Max only): OpenAI (GPT-4.5/5/4o), Anthropic (Claude 3.5 Sonnet/Opus/Haiku), Google Vertex (Gemini 4 Ultra), Perplexity (Sonar Pro / Reasoning / Deep Research).

The router enforces tier access via `PLAN_PROVIDER_ACCESS`.

### Stages (per plan)

- **Free / Plus** → 1-stage (direct call).
- **Pro** → up to 2-stage (Search + Reasoning).
- **Max** → up to 3-stage (Search + Reasoning + Verifier).

## Project layout

```
main.py            Bothost entry point shim
bot/
  core/            router, pipeline, context_manager, rate_limit, i18n
  config/          settings.py (single source of truth) + shared_path() helper
  db/              SQLAlchemy models + Alembic migrations
  handlers/        aiogram routers
  services/        payments, promo, channels, crypto rates
    ai_providers/  per-provider HTTP clients (free + paid tiers)
  locale/          ru/, en/ JSON message catalogues
  main.py
```

## Bothost.ru deployment notes

- `DATABASE_URL` must point to the host-provided PostgreSQL instance (e.g. `postgresql+asyncpg://...`). SQLite is allowed for local dev only.
- `SHARED_DIR` defaults to `/app/shared` — used for rotating log files (`logs/bot.log`) and any shared assets. The directory is created automatically on first use, with a fallback to `<repo>/.shared` if the host path is read-only.
- `BOT_TOKEN` and at least one provider key must be set in the host's environment before boot.
- Connection pool sizing is controlled by `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_S`.

## Admin

Default admin Telegram ID is `2080411409`. Add more via `ADMIN_IDS` (comma separated).

## Payments

- Telegram Stars (native invoices).
- Crypto Bot via [`aiocryptopay`](https://github.com/layerqa/aiocryptopay) (TON / USDT / BTC) using `CRYPTO_BOT_TOKEN`. Crypto USD rates are pulled from CryptoBot's `getExchangeRates` first, with CoinGecko as a fallback.
- Manual: `@keedboy016`.

USD is the base currency. Promo codes support `sponsor_only` / `requires_active_subscription` / `min_plan_required` and are enforced both when applied and at checkout.
