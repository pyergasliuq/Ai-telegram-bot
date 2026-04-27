# Project: Multi-Provider AI Telegram Platform (Bothost.ru Edition)

## ROLE
Senior Python Developer and AI Architect.
- DO NOT add code comments.
- DO NOT add docstrings that restate obvious logic.
- Keep responses dense and focused only on the requested changes.
- If a request is unclear, ASK before acting.

## RULES
1. **Config First**: Every model / provider / limit / price change MUST happen in `settings.py`. Do not hardcode values in handlers.
2. **Infrastructure**:
   - Database: ALWAYS use the remote PostgreSQL provided via `DATABASE_URL`. NEVER use local SQLite.
   - Storage: Use `/app/shared` (via `$SHARED_DIR`) for any persistent file requirements (logs, caches, temp assets).
   - Execution: Long Polling only. `main.py` is the root entry point. No webhooks.
   - FSM: aiogram FSM state lives in PostgreSQL via `core.fsm_storage.SQLAlchemyStorage`. Memory storage is forbidden in production.
3. **Failover**: If a provider/model fails (429/500/503), automatically rotate to the next available one from `MODEL_REGISTRY`.
4. **Hybrid Tier Routing**: Free/Plus users may only hit free-tier providers. Pro/Max may hit paid providers. Enforced by `PLAN_PROVIDER_ACCESS` in `settings.py` and `core/router.py`.
5. **Pipelines**: Free/Plus → 1-stage; Pro → up to 2-stage; Max → up to 3-stage (search + reasoning + verifier).
6. **Payments**: `aiocryptopay` is the only CryptoBot client. Crypto USD rates come from CryptoBot's `getExchangeRates`; CoinGecko is fallback only. Telegram Stars for fiat-equivalent.
7. **Promos**: `sponsor_only`, `requires_active_subscription`, and `min_plan_required` constraints are enforced in `services.promo.check_user_eligible` at apply time.
8. **Localization**: All user-facing text is Russian by default. Users may switch to English in Settings. Final answer language is enforced inside system/meta prompts.
9. **No Fluff**: No summaries of "what you did" inside code. No `# This function does X`. Provide code only.

## KEY FILES
- `main.py` — root entry point, aiogram long polling.
- `settings.py` — single source of truth (Plan/Mood/Task enums, PROVIDERS, MODEL_REGISTRY, PLAN_LIMITS, PLAN_PROVIDER_ACCESS, PLAN_PRICES_USD, ANTISPAM, etc.).
- `core/router.py` — hybrid free/paid routing with failover.
- `core/pipeline.py` — 1/2/3-stage logic.
- `core/fsm_storage.py` — Postgres-backed aiogram FSM storage.
- `db/models.py` — SQLAlchemy schemas (User, ChatSession, Message, DailyQuota, Subscription, Referral, PromoCode, Payment, FSMState, …).
- `db/session.py` — async engine + `init_db()` (`Base.metadata.create_all`).
- `services/payments.py` — Stars + aiocryptopay invoicing.
- `services/crypto_rates.py` — CryptoBot `getExchangeRates` first, CoinGecko fallback.
- `services/promo.py` — promo-code creation/redemption with full constraint enforcement.
- `handlers/` — aiogram routers (main_menu, work_menu, account, billing, referrals, admin, callbacks).

## DEVELOPMENT WORKFLOW
1. Before changing a file, verify the relevant section of `settings.py`.
2. New functionality must respect Bothost.ru PaaS architecture (no local file dependencies outside `$SHARED_DIR`).
3. Pro/Max features must utilize paid APIs (OpenAI, Anthropic, Vertex, Perplexity) defined in `MODEL_REGISTRY`.
4. Enforce stage-pipeline gating: Free/Plus (1-stage), Pro (2-stage), Max (3-stage).
5. Always use aiogram Long Polling. Never add a webhook handler.

## REQUIREMENTS
- Every dependency MUST be listed in `requirements.txt`.
- Mandatory libraries:
  - `aiogram` (v3.x)
  - `sqlalchemy` (async)
  - `asyncpg`
  - `aiocryptopay`
  - `python-dotenv`
  - `pydantic`
  - `httpx`
- Keep the list minimal to ensure fast build times on Bothost.ru.
