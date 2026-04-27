from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Plan(StrEnum):
    FREE = "free"
    PLUS = "plus"
    PRO = "pro"
    MAX = "max"


class SpeedMode(StrEnum):
    FAST = "fast"
    BALANCE = "balance"
    MAX = "max"


class StageMode(StrEnum):
    ONE = "one"
    TWO = "two"
    THREE = "three"


class TaskType(StrEnum):
    TEXT_GENERAL = "text_general"
    TEXT_REASONING = "text_reasoning"
    CODE = "code"
    SUMMARIZER = "summarizer"
    SEARCH = "search"
    IMAGE = "image"
    TTS = "tts"
    STT = "stt"
    VERIFIER = "verifier"


class Mood(StrEnum):
    FRIENDLY = "friendly"
    STRICT_FACTS = "strict_facts"
    TOUGH_HONEST = "tough_honest"
    TEACHER = "teacher"
    HUMAN_CODER = "human_coder"
    SMART_FRIEND = "smart_friend"


class TaskPreset(StrEnum):
    CODE = "code"
    COPY = "copy"
    PRESENTATION = "presentation"
    REASONING = "reasoning"
    TRANSLATION = "translation"
    CREATIVE = "creative"
    DOCUMENTS = "documents"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    BOT_TOKEN: str = ""
    ADMIN_IDS_RAW: str = Field(default="2080411409", alias="ADMIN_IDS")
    DEFAULT_LANGUAGE: str = "ru"

    DATABASE_URL: str = "postgresql+asyncpg://aibot:aibot@localhost:5432/aibot"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_S: int = 1800
    REDIS_URL: str = ""

    SHARED_DIR: str = "/app/shared"

    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    ONLYSQ_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    SAMBANOVA_API_KEY: str = ""
    CLOUDFLARE_API_KEY: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    FIREWORKS_API_KEY: str = ""

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    VERTEX_API_KEY: str = ""
    VERTEX_PROJECT: str = ""
    VERTEX_LOCATION: str = "us-central1"
    PERPLEXITY_API_KEY: str = ""

    CRYPTO_BOT_TOKEN: str = ""
    CRYPTO_BOT_TESTNET: bool = False

    COINGECKO_API_KEY: str = ""

    LOG_LEVEL: str = "INFO"

    DEFAULT_ADMIN_ID: int = 2080411409
    MANUAL_PAYMENT_CONTACT: str = "@keedboy016"

    REQUEST_TIMEOUT_S: int = 60
    PROVIDER_COOLDOWN_S: int = 120
    SUMMARIZE_EVERY_N_MESSAGES: int = 4
    KEEP_RECENT_MESSAGES: int = 30

    @computed_field  # type: ignore[misc]
    @property
    def ADMIN_IDS(self) -> set[int]:
        ids: set[int] = {self.DEFAULT_ADMIN_ID}
        for raw in self.ADMIN_IDS_RAW.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.add(int(raw))
        return ids


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def shared_path(*parts: str) -> Path:
    base = Path(settings.SHARED_DIR)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = PROJECT_ROOT / ".shared"
        base.mkdir(parents=True, exist_ok=True)
    p = base.joinpath(*parts) if parts else base
    if parts:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


FREE_TIER_PROVIDERS: set[str] = {
    "google",
    "groq",
    "openrouter",
    "huggingface",
    "onlysq",
    "together",
    "cerebras",
    "sambanova",
    "cloudflare",
    "fireworks",
}

PAID_TIER_PROVIDERS: set[str] = {
    "openai",
    "anthropic",
    "vertex",
    "perplexity",
}

PLAN_PROVIDER_ACCESS: dict[Plan, set[str]] = {
    Plan.FREE: FREE_TIER_PROVIDERS,
    Plan.PLUS: FREE_TIER_PROVIDERS,
    Plan.PRO: FREE_TIER_PROVIDERS | PAID_TIER_PROVIDERS,
    Plan.MAX: FREE_TIER_PROVIDERS | PAID_TIER_PROVIDERS,
}


PLAN_LIMITS: dict[Plan, dict[str, int]] = {
    Plan.FREE: {
        "text": 10,
        "images": 2,
        "stt": 1,
        "tts": 0,
        "rpm": 4,
        "max_message_chars": 2000,
    },
    Plan.PLUS: {
        "text": 25,
        "images": 5,
        "stt": 10,
        "tts": 10,
        "rpm": 12,
        "max_message_chars": 6000,
    },
    Plan.PRO: {
        "text": 100,
        "images": 10,
        "stt": 50,
        "tts": 50,
        "rpm": 30,
        "max_message_chars": 20000,
    },
    Plan.MAX: {
        "text": 5000,
        "images": 500,
        "stt": 1000,
        "tts": 1000,
        "rpm": 60,
        "max_message_chars": 60000,
    },
}


PLAN_FEATURES: dict[Plan, dict[str, Any]] = {
    Plan.FREE: {
        "speed_modes": [SpeedMode.FAST],
        "stages": [StageMode.ONE],
        "moods": [Mood.FRIENDLY, Mood.SMART_FRIEND],
        "task_presets": [TaskPreset.CODE, TaskPreset.COPY, TaskPreset.REASONING],
        "context_seamless": False,
    },
    Plan.PLUS: {
        "speed_modes": [SpeedMode.FAST, SpeedMode.BALANCE],
        "stages": [StageMode.ONE],
        "moods": list(Mood),
        "task_presets": list(TaskPreset),
        "context_seamless": False,
    },
    Plan.PRO: {
        "speed_modes": list(SpeedMode),
        "stages": [StageMode.ONE, StageMode.TWO],
        "moods": list(Mood),
        "task_presets": list(TaskPreset),
        "context_seamless": False,
    },
    Plan.MAX: {
        "speed_modes": list(SpeedMode),
        "stages": list(StageMode),
        "moods": list(Mood),
        "task_presets": list(TaskPreset),
        "context_seamless": True,
    },
}


PLAN_DURATIONS: dict[str, int] = {
    "1w": 7,
    "2w": 14,
    "1m": 30,
    "3m": 90,
}


PLAN_PRICES_USD: dict[Plan, dict[str, Decimal]] = {
    Plan.PLUS: {
        "1w": Decimal("1.99"),
        "2w": Decimal("3.49"),
        "1m": Decimal("5.99"),
        "3m": Decimal("14.99"),
    },
    Plan.PRO: {
        "1w": Decimal("4.99"),
        "2w": Decimal("8.99"),
        "1m": Decimal("14.99"),
        "3m": Decimal("39.99"),
    },
    Plan.MAX: {
        "1w": Decimal("9.99"),
        "2w": Decimal("17.99"),
        "1m": Decimal("29.99"),
        "3m": Decimal("79.99"),
    },
}


STARS_PER_USD: int = 75


TRIALS: dict[Plan, dict[str, int]] = {
    Plan.PLUS: {"stars": 1, "days": 3},
    Plan.PRO: {"stars": 5, "days": 3},
    Plan.MAX: {"stars": 10, "days": 3},
}


CRYPTO_ASSETS: list[str] = ["TON", "USDT", "BTC"]
CRYPTO_RATE_TTL_S: int = 600


REFERRAL_REWARD_TEXT_REQUESTS: int = 1
REFERRAL_REWARD_DURATION_DIVIDER: int = 4
REFERRAL_PROMO_THRESHOLD: int = 5


PROMO_DISCOUNT_MIN: int = 5
PROMO_DISCOUNT_MAX: int = 20
USER_PROMO_DISCOUNT_MIN: int = 15
USER_PROMO_DISCOUNT_MAX: int = 20


ANTISPAM: dict[str, int] = {
    "burst_window_s": 4,
    "burst_max": 5,
    "cooldown_s": 8,
    "max_pending_per_user": 1,
}


PROVIDERS: dict[str, dict[str, Any]] = {
    "google": {
        "active": True,
        "tier": "free",
        "key_env": "GOOGLE_API_KEY",
        "models": {
            "gemini-2.5-flash": {"rpm": 15, "tpm": 1_000_000, "tags": ["text", "fast", "balance"]},
            "gemini-2.5-flash-lite": {"rpm": 30, "tpm": 1_000_000, "tags": ["text", "fast", "summarizer"]},
            "gemini-2.5-pro": {"rpm": 5, "tpm": 1_000_000, "tags": ["text", "max", "reasoning"]},
            "gemini-3-flash": {"rpm": 10, "tpm": 1_000_000, "tags": ["text", "balance"]},
            "gemini-3-pro": {"rpm": 5, "tpm": 1_000_000, "tags": ["text", "max", "reasoning"]},
            "gemini-4-flash": {"rpm": 10, "tpm": 1_000_000, "tags": ["text", "balance"]},
            "gemini-4-pro": {"rpm": 5, "tpm": 1_000_000, "tags": ["text", "max", "reasoning"]},
            "gemma-3-27b": {"rpm": 30, "tpm": 1_000_000, "tags": ["text", "fast", "summarizer"]},
            "gemma-4-31b": {"rpm": 30, "tpm": 1_000_000, "tags": ["text", "fast", "summarizer"]},
            "gemini-2.5-flash-image": {"rpm": 10, "tpm": 0, "tags": ["image"]},
            "gemini-2.5-native-audio": {"rpm": 10, "tpm": 0, "tags": ["stt", "tts"]},
            "gemini-2.5-tts": {"rpm": 10, "tpm": 0, "tags": ["tts"]},
        },
    },
    "groq": {
        "active": True,
        "tier": "free",
        "key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": {
            "llama-3.1-8b-instant": {"rpm": 30, "tags": ["text", "fast", "summarizer"]},
            "llama-3.3-70b-versatile": {"rpm": 30, "tags": ["text", "balance", "reasoning"]},
            "mixtral-8x7b-32768": {"rpm": 30, "tags": ["text", "balance"]},
            "qwen-2.5-32b": {"rpm": 30, "tags": ["text", "balance"]},
            "openai/gpt-oss-20b": {"rpm": 20, "tags": ["text", "balance", "code"]},
            "openai/gpt-oss-120b": {"rpm": 10, "tags": ["text", "max", "reasoning"]},
            "whisper-large-v3": {"rpm": 30, "tags": ["stt"]},
        },
    },
    "openrouter": {
        "active": True,
        "tier": "free",
        "key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "deepseek/deepseek-chat-v3-0324:free": {"rpm": 20, "tags": ["text", "balance", "reasoning"]},
            "deepseek/deepseek-r1:free": {"rpm": 20, "tags": ["text", "max", "reasoning", "verifier"]},
            "deepseek/deepseek-v4-flash:free": {"rpm": 20, "tags": ["text", "balance", "reasoning"]},
            "deepseek/deepseek-v4-pro:free": {"rpm": 10, "tags": ["text", "max", "reasoning", "verifier"]},
            "qwen/qwen3-235b-a22b:free": {"rpm": 20, "tags": ["text", "max", "reasoning"]},
            "qwen/qwen3-coder:free": {"rpm": 20, "tags": ["text", "code"]},
            "qwen/qwen-2.5-72b-instruct:free": {"rpm": 20, "tags": ["text", "balance"]},
            "meta-llama/llama-3.3-70b-instruct:free": {"rpm": 20, "tags": ["text", "balance"]},
            "moonshotai/kimi-k2:free": {"rpm": 20, "tags": ["text", "balance", "search"]},
            "moonshotai/kimi-k2.5:free": {"rpm": 15, "tags": ["text", "balance", "search", "reasoning"]},
            "google/gemini-2.0-flash-exp:free": {"rpm": 20, "tags": ["text", "fast"]},
            "perplexity/sonar-reasoning": {"rpm": 10, "tags": ["text", "search", "verifier"]},
            "perplexity/searchgpt-pro": {"rpm": 10, "tags": ["text", "search"]},
        },
    },
    "huggingface": {
        "active": False,
        "tier": "free",
        "key_env": "HUGGINGFACE_API_KEY",
        "base_url": "https://api-inference.huggingface.co",
        "models": {
            "meta-llama/Meta-Llama-3-8B-Instruct": {"rpm": 30, "tags": ["text", "fast"]},
            "Qwen/Qwen2.5-7B-Instruct": {"rpm": 30, "tags": ["text", "fast", "summarizer"]},
        },
    },
    "onlysq": {
        "active": True,
        "tier": "free",
        "key_env": "ONLYSQ_API_KEY",
        "base_url": "https://api.onlysq.ru/ai/v2",
        "models": {
            "gpt-3.5-turbo": {"rpm": 30, "tags": ["text", "fast"]},
            "gpt-4o-mini": {"rpm": 30, "tags": ["text", "balance"]},
            "gpt-4o": {"rpm": 15, "tags": ["text", "max", "reasoning"]},
            "gpt-5-mini": {"rpm": 15, "tags": ["text", "balance", "reasoning"]},
            "gpt-5": {"rpm": 5, "tags": ["text", "max", "reasoning", "verifier"]},
            "claude-sonnet-4": {"rpm": 10, "tags": ["text", "max", "reasoning", "verifier"]},
            "deepseek-v3": {"rpm": 20, "tags": ["text", "balance", "reasoning"]},
            "deepseek-r1": {"rpm": 10, "tags": ["text", "max", "reasoning", "verifier"]},
            "qwen-3-max": {"rpm": 10, "tags": ["text", "max", "reasoning"]},
            "sonar": {"rpm": 10, "tags": ["text", "search"]},
            "sonar-reasoning-pro": {"rpm": 5, "tags": ["text", "search", "verifier"]},
            "flux-schnell": {"rpm": 10, "tags": ["image"]},
            "flux-dev": {"rpm": 5, "tags": ["image"]},
        },
    },
    "together": {
        "active": True,
        "tier": "free",
        "key_env": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "models": {
            "deepseek-ai/DeepSeek-V3": {"rpm": 20, "tags": ["text", "balance", "reasoning"]},
            "deepseek-ai/DeepSeek-R1": {"rpm": 10, "tags": ["text", "max", "reasoning", "verifier"]},
            "moonshotai/Kimi-K2-Instruct": {"rpm": 20, "tags": ["text", "balance", "search"]},
            "Qwen/Qwen2.5-72B-Instruct-Turbo": {"rpm": 20, "tags": ["text", "balance"]},
            "Qwen/Qwen3-235B-A22B-Instruct-2507-tput": {"rpm": 10, "tags": ["text", "max", "reasoning"]},
            "meta-llama/Llama-3.3-70B-Instruct-Turbo": {"rpm": 20, "tags": ["text", "balance"]},
            "mistralai/Mixtral-8x7B-Instruct-v0.1": {"rpm": 20, "tags": ["text", "balance"]},
            "cartesia/sonic-3": {"rpm": 20, "tags": ["tts"]},
            "openai/whisper-large-v3": {"rpm": 30, "tags": ["stt"]},
            "black-forest-labs/FLUX.1-schnell-Free": {"rpm": 10, "tags": ["image"]},
        },
    },
    "cerebras": {
        "active": True,
        "tier": "free",
        "key_env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "models": {
            "llama-3.3-70b": {"rpm": 30, "tags": ["text", "balance", "reasoning"]},
            "llama3.1-8b": {"rpm": 30, "tags": ["text", "fast", "summarizer"]},
            "qwen-3-32b": {"rpm": 30, "tags": ["text", "balance"]},
            "gpt-oss-120b": {"rpm": 15, "tags": ["text", "max", "reasoning"]},
        },
    },
    "sambanova": {
        "active": True,
        "tier": "free",
        "key_env": "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
        "models": {
            "Meta-Llama-3.3-70B-Instruct": {"rpm": 20, "tags": ["text", "balance", "reasoning"]},
            "Meta-Llama-3.1-8B-Instruct": {"rpm": 30, "tags": ["text", "fast", "summarizer"]},
            "Qwen2.5-72B-Instruct": {"rpm": 20, "tags": ["text", "balance"]},
            "QwQ-32B-Preview": {"rpm": 10, "tags": ["text", "reasoning", "verifier"]},
            "DeepSeek-V3-0324": {"rpm": 10, "tags": ["text", "max", "reasoning"]},
        },
    },
    "cloudflare": {
        "active": True,
        "tier": "free",
        "key_env": "CLOUDFLARE_API_KEY",
        "models": {
            "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {"rpm": 20, "tags": ["text", "balance"]},
            "@cf/meta/llama-3.1-8b-instruct": {"rpm": 30, "tags": ["text", "fast"]},
            "@cf/google/gemma-3-12b-it": {"rpm": 30, "tags": ["text", "fast", "summarizer"]},
            "@cf/qwen/qwen2.5-coder-32b-instruct": {"rpm": 20, "tags": ["text", "code"]},
            "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b": {"rpm": 10, "tags": ["text", "reasoning"]},
            "@cf/openai/gpt-oss-20b": {"rpm": 20, "tags": ["text", "balance", "code"]},
            "@cf/black-forest-labs/flux-1-schnell": {"rpm": 10, "tags": ["image"]},
            "@cf/openai/whisper-large-v3-turbo": {"rpm": 30, "tags": ["stt"]},
        },
    },
    "fireworks": {
        "active": True,
        "tier": "free",
        "key_env": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models": {
            "accounts/fireworks/models/llama-v3p3-70b-instruct": {"rpm": 20, "tags": ["text", "balance"]},
            "accounts/fireworks/models/deepseek-v3": {"rpm": 10, "tags": ["text", "max", "reasoning"]},
            "accounts/fireworks/models/deepseek-r1": {"rpm": 5, "tags": ["text", "max", "reasoning", "verifier"]},
            "accounts/fireworks/models/qwen3-235b-a22b": {"rpm": 5, "tags": ["text", "max", "reasoning"]},
        },
    },
    "openai": {
        "active": True,
        "tier": "paid",
        "key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "gpt-4.5": {"rpm": 60, "tags": ["text", "balance", "reasoning"]},
            "gpt-5": {"rpm": 60, "tags": ["text", "max", "reasoning", "verifier"]},
            "gpt-5-mini": {"rpm": 120, "tags": ["text", "balance", "reasoning"]},
            "gpt-4o": {"rpm": 60, "tags": ["text", "balance", "reasoning"]},
            "gpt-4o-mini": {"rpm": 120, "tags": ["text", "fast"]},
            "o4-mini": {"rpm": 60, "tags": ["text", "balance", "reasoning"]},
            "dall-e-3": {"rpm": 30, "tags": ["image"]},
            "whisper-1": {"rpm": 60, "tags": ["stt"]},
            "tts-1-hd": {"rpm": 60, "tags": ["tts"]},
        },
    },
    "anthropic": {
        "active": True,
        "tier": "paid",
        "key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "models": {
            "claude-3-5-sonnet-latest": {"rpm": 50, "tags": ["text", "balance", "reasoning", "verifier"]},
            "claude-3-5-opus-latest": {"rpm": 30, "tags": ["text", "max", "reasoning", "verifier"]},
            "claude-3-5-haiku-latest": {"rpm": 100, "tags": ["text", "fast", "summarizer"]},
        },
    },
    "vertex": {
        "active": True,
        "tier": "paid",
        "key_env": "VERTEX_API_KEY",
        "models": {
            "gemini-4-ultra": {"rpm": 30, "tags": ["text", "max", "reasoning", "verifier"]},
            "gemini-4-pro": {"rpm": 30, "tags": ["text", "max", "reasoning"]},
            "gemini-4-flash": {"rpm": 60, "tags": ["text", "balance"]},
            "gemini-3-pro": {"rpm": 30, "tags": ["text", "max", "reasoning"]},
        },
    },
    "perplexity": {
        "active": True,
        "tier": "paid",
        "key_env": "PERPLEXITY_API_KEY",
        "base_url": "https://api.perplexity.ai",
        "models": {
            "sonar": {"rpm": 60, "tags": ["text", "search"]},
            "sonar-pro": {"rpm": 30, "tags": ["text", "search", "reasoning"]},
            "sonar-reasoning-pro": {"rpm": 30, "tags": ["text", "search", "reasoning", "verifier"]},
            "sonar-deep-research": {"rpm": 10, "tags": ["text", "search", "reasoning"]},
        },
    },
}


def _m(provider: str, model: str) -> tuple[str, str]:
    return provider, model


MODEL_REGISTRY: dict[Plan, dict[TaskType, list[tuple[str, str]]]] = {
    Plan.FREE: {
        TaskType.TEXT_GENERAL: [
            _m("groq", "llama-3.1-8b-instant"),
            _m("cerebras", "llama3.1-8b"),
            _m("cloudflare", "@cf/google/gemma-3-12b-it"),
            _m("google", "gemma-3-27b"),
            _m("sambanova", "Meta-Llama-3.1-8B-Instruct"),
            _m("openrouter", "google/gemini-2.0-flash-exp:free"),
            _m("onlysq", "gpt-3.5-turbo"),
        ],
        TaskType.TEXT_REASONING: [
            _m("groq", "llama-3.1-8b-instant"),
            _m("cerebras", "llama3.1-8b"),
            _m("google", "gemma-4-31b"),
        ],
        TaskType.CODE: [
            _m("groq", "openai/gpt-oss-20b"),
            _m("cloudflare", "@cf/qwen/qwen2.5-coder-32b-instruct"),
            _m("openrouter", "qwen/qwen3-coder:free"),
        ],
        TaskType.SUMMARIZER: [
            _m("groq", "llama-3.1-8b-instant"),
            _m("google", "gemma-3-27b"),
            _m("cloudflare", "@cf/google/gemma-3-12b-it"),
            _m("cerebras", "llama3.1-8b"),
        ],
        TaskType.SEARCH: [
            _m("openrouter", "moonshotai/kimi-k2:free"),
            _m("onlysq", "sonar"),
        ],
        TaskType.IMAGE: [
            _m("cloudflare", "@cf/black-forest-labs/flux-1-schnell"),
            _m("together", "black-forest-labs/FLUX.1-schnell-Free"),
            _m("onlysq", "flux-schnell"),
        ],
        TaskType.STT: [
            _m("groq", "whisper-large-v3"),
            _m("cloudflare", "@cf/openai/whisper-large-v3-turbo"),
            _m("together", "openai/whisper-large-v3"),
        ],
        TaskType.TTS: [],
        TaskType.VERIFIER: [],
    },
    Plan.PLUS: {
        TaskType.TEXT_GENERAL: [
            _m("groq", "llama-3.3-70b-versatile"),
            _m("cerebras", "llama-3.3-70b"),
            _m("sambanova", "Meta-Llama-3.3-70B-Instruct"),
            _m("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            _m("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
            _m("google", "gemini-2.5-flash"),
            _m("onlysq", "gpt-4o-mini"),
        ],
        TaskType.TEXT_REASONING: [
            _m("groq", "llama-3.3-70b-versatile"),
            _m("cerebras", "llama-3.3-70b"),
            _m("google", "gemini-2.5-flash"),
            _m("openrouter", "deepseek/deepseek-chat-v3-0324:free"),
            _m("together", "deepseek-ai/DeepSeek-V3"),
        ],
        TaskType.CODE: [
            _m("groq", "openai/gpt-oss-20b"),
            _m("cloudflare", "@cf/qwen/qwen2.5-coder-32b-instruct"),
            _m("openrouter", "qwen/qwen3-coder:free"),
            _m("onlysq", "gpt-4o-mini"),
        ],
        TaskType.SUMMARIZER: [
            _m("groq", "llama-3.1-8b-instant"),
            _m("google", "gemma-4-31b"),
            _m("cerebras", "llama3.1-8b"),
        ],
        TaskType.SEARCH: [
            _m("openrouter", "moonshotai/kimi-k2:free"),
            _m("onlysq", "sonar"),
            _m("together", "moonshotai/Kimi-K2-Instruct"),
        ],
        TaskType.IMAGE: [
            _m("cloudflare", "@cf/black-forest-labs/flux-1-schnell"),
            _m("together", "black-forest-labs/FLUX.1-schnell-Free"),
            _m("onlysq", "flux-schnell"),
            _m("google", "gemini-2.5-flash-image"),
        ],
        TaskType.STT: [
            _m("groq", "whisper-large-v3"),
            _m("cloudflare", "@cf/openai/whisper-large-v3-turbo"),
        ],
        TaskType.TTS: [
            _m("google", "gemini-2.5-tts"),
            _m("together", "cartesia/sonic-3"),
        ],
        TaskType.VERIFIER: [
            _m("openrouter", "deepseek/deepseek-r1:free"),
            _m("together", "deepseek-ai/DeepSeek-R1"),
        ],
    },
    Plan.PRO: {
        TaskType.TEXT_GENERAL: [
            _m("openai", "gpt-5-mini"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("vertex", "gemini-4-pro"),
            _m("google", "gemini-2.5-pro"),
            _m("openrouter", "deepseek/deepseek-v4-pro:free"),
            _m("openrouter", "qwen/qwen3-235b-a22b:free"),
            _m("together", "Qwen/Qwen3-235B-A22B-Instruct-2507-tput"),
            _m("groq", "llama-3.3-70b-versatile"),
            _m("cerebras", "gpt-oss-120b"),
            _m("onlysq", "gpt-4o"),
        ],
        TaskType.TEXT_REASONING: [
            _m("openai", "gpt-5"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("vertex", "gemini-4-pro"),
            _m("openrouter", "deepseek/deepseek-v4-pro:free"),
            _m("openrouter", "deepseek/deepseek-r1:free"),
            _m("together", "deepseek-ai/DeepSeek-R1"),
            _m("google", "gemini-3-pro"),
            _m("onlysq", "deepseek-r1"),
            _m("fireworks", "accounts/fireworks/models/deepseek-r1"),
            _m("sambanova", "DeepSeek-V3-0324"),
        ],
        TaskType.CODE: [
            _m("openai", "gpt-5"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("openrouter", "qwen/qwen3-coder:free"),
            _m("groq", "openai/gpt-oss-120b"),
            _m("cloudflare", "@cf/qwen/qwen2.5-coder-32b-instruct"),
            _m("onlysq", "gpt-4o"),
        ],
        TaskType.SUMMARIZER: [
            _m("anthropic", "claude-3-5-haiku-latest"),
            _m("groq", "llama-3.1-8b-instant"),
            _m("google", "gemma-4-31b"),
            _m("cerebras", "llama3.1-8b"),
        ],
        TaskType.SEARCH: [
            _m("perplexity", "sonar-pro"),
            _m("perplexity", "sonar-reasoning-pro"),
            _m("onlysq", "sonar-reasoning-pro"),
            _m("openrouter", "perplexity/sonar-reasoning"),
            _m("openrouter", "moonshotai/kimi-k2.5:free"),
            _m("openrouter", "moonshotai/kimi-k2:free"),
        ],
        TaskType.IMAGE: [
            _m("openai", "dall-e-3"),
            _m("google", "gemini-2.5-flash-image"),
            _m("onlysq", "flux-dev"),
            _m("cloudflare", "@cf/black-forest-labs/flux-1-schnell"),
        ],
        TaskType.STT: [
            _m("openai", "whisper-1"),
            _m("groq", "whisper-large-v3"),
            _m("together", "openai/whisper-large-v3"),
        ],
        TaskType.TTS: [
            _m("openai", "tts-1-hd"),
            _m("google", "gemini-2.5-tts"),
            _m("together", "cartesia/sonic-3"),
        ],
        TaskType.VERIFIER: [
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("openai", "gpt-5"),
            _m("perplexity", "sonar-reasoning-pro"),
            _m("onlysq", "claude-sonnet-4"),
            _m("openrouter", "deepseek/deepseek-r1:free"),
            _m("together", "deepseek-ai/DeepSeek-R1"),
        ],
    },
    Plan.MAX: {
        TaskType.TEXT_GENERAL: [
            _m("vertex", "gemini-4-ultra"),
            _m("openai", "gpt-5"),
            _m("anthropic", "claude-3-5-opus-latest"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("vertex", "gemini-4-pro"),
            _m("google", "gemini-4-pro"),
            _m("google", "gemini-3-pro"),
            _m("onlysq", "gpt-5"),
            _m("onlysq", "claude-sonnet-4"),
            _m("openrouter", "deepseek/deepseek-v4-pro:free"),
            _m("openrouter", "qwen/qwen3-235b-a22b:free"),
            _m("together", "Qwen/Qwen3-235B-A22B-Instruct-2507-tput"),
        ],
        TaskType.TEXT_REASONING: [
            _m("vertex", "gemini-4-ultra"),
            _m("openai", "gpt-5"),
            _m("anthropic", "claude-3-5-opus-latest"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("onlysq", "gpt-5"),
            _m("onlysq", "claude-sonnet-4"),
            _m("onlysq", "deepseek-r1"),
            _m("openrouter", "deepseek/deepseek-v4-pro:free"),
            _m("openrouter", "deepseek/deepseek-r1:free"),
            _m("together", "deepseek-ai/DeepSeek-R1"),
            _m("google", "gemini-4-pro"),
            _m("fireworks", "accounts/fireworks/models/deepseek-r1"),
        ],
        TaskType.CODE: [
            _m("openai", "gpt-5"),
            _m("anthropic", "claude-3-5-sonnet-latest"),
            _m("onlysq", "gpt-5"),
            _m("onlysq", "claude-sonnet-4"),
            _m("openrouter", "qwen/qwen3-coder:free"),
            _m("groq", "openai/gpt-oss-120b"),
        ],
        TaskType.SUMMARIZER: [
            _m("anthropic", "claude-3-5-haiku-latest"),
            _m("google", "gemma-4-31b"),
            _m("groq", "llama-3.1-8b-instant"),
            _m("cerebras", "llama3.1-8b"),
        ],
        TaskType.SEARCH: [
            _m("perplexity", "sonar-deep-research"),
            _m("perplexity", "sonar-reasoning-pro"),
            _m("perplexity", "sonar-pro"),
            _m("onlysq", "sonar-reasoning-pro"),
            _m("openrouter", "perplexity/sonar-reasoning"),
            _m("openrouter", "moonshotai/kimi-k2.5:free"),
        ],
        TaskType.IMAGE: [
            _m("openai", "dall-e-3"),
            _m("google", "gemini-2.5-flash-image"),
            _m("onlysq", "flux-dev"),
            _m("together", "black-forest-labs/FLUX.1-schnell-Free"),
        ],
        TaskType.STT: [
            _m("openai", "whisper-1"),
            _m("groq", "whisper-large-v3"),
            _m("together", "openai/whisper-large-v3"),
            _m("cloudflare", "@cf/openai/whisper-large-v3-turbo"),
        ],
        TaskType.TTS: [
            _m("openai", "tts-1-hd"),
            _m("google", "gemini-2.5-tts"),
            _m("together", "cartesia/sonic-3"),
        ],
        TaskType.VERIFIER: [
            _m("anthropic", "claude-3-5-opus-latest"),
            _m("openai", "gpt-5"),
            _m("vertex", "gemini-4-ultra"),
            _m("perplexity", "sonar-reasoning-pro"),
            _m("onlysq", "claude-sonnet-4"),
            _m("onlysq", "gpt-5"),
            _m("openrouter", "deepseek/deepseek-r1:free"),
        ],
    },
}


SPEED_TAG_MAP: dict[SpeedMode, str] = {
    SpeedMode.FAST: "fast",
    SpeedMode.BALANCE: "balance",
    SpeedMode.MAX: "max",
}


MOOD_PROMPTS: dict[Mood, str] = {
    Mood.FRIENDLY: (
        "You speak like a friendly, supportive human. You use simple, clear language, "
        "occasional light humor, and encourage the user."
    ),
    Mood.STRICT_FACTS: (
        "You are concise and to the point. You avoid small talk, focus on facts, structure, "
        "and clarity. You answer only what is asked."
    ),
    Mood.TOUGH_HONEST: (
        "You speak directly and bluntly, but not offensively. You point out mistakes clearly, "
        "suggest improvements, and do not sugarcoat problems."
    ),
    Mood.TEACHER: (
        "You are a patient teacher. You explain complex ideas step by step with examples, "
        "check user understanding, and avoid jargon."
    ),
    Mood.HUMAN_CODER: (
        "You are a senior developer who explains code like a colleague. You write clean, "
        "modern code, give short explanations, and avoid unnecessary theory."
    ),
    Mood.SMART_FRIEND: (
        "You talk like a smart friend, natural and informal, but you still give accurate, "
        "well-structured answers."
    ),
}


TASK_PROMPTS: dict[TaskPreset, str] = {
    TaskPreset.CODE: (
        "You are a senior software engineer. You write production-quality code, prefer clear "
        "structure and readability. You avoid non-existent libraries. You include short, useful "
        "explanations after the code."
    ),
    TaskPreset.COPY: (
        "You are a professional copywriter. You write engaging, clear texts for the target "
        "audience. You adapt tone to the mood preset."
    ),
    TaskPreset.PRESENTATION: (
        "You create structured plans for presentations, talks or reports: sections, bullet "
        "points, transitions. You focus on clarity and logical flow."
    ),
    TaskPreset.REASONING: (
        "You are an analytical assistant. You explain your reasoning step by step internally "
        "but show only clean, concise final answers (unless user explicitly asks for chain-of-thought)."
    ),
    TaskPreset.TRANSLATION: (
        "You are a professional translator. You preserve meaning and style, adapt idioms, and "
        "avoid literal word-for-word translation."
    ),
    TaskPreset.CREATIVE: (
        "You are a creative writer and idea generator. You propose original ideas, plots, "
        "characters or scenarios, following the chosen mood."
    ),
    TaskPreset.DOCUMENTS: (
        "You create formal and semi-formal documents: resumes, cover letters, business emails, "
        "and reports with appropriate tone and structure."
    ),
}


WORK_CATEGORIES: list[dict[str, Any]] = [
    {"id": "text_chat", "task_preset": TaskPreset.COPY, "task_type": TaskType.TEXT_GENERAL},
    {"id": "code", "task_preset": TaskPreset.CODE, "task_type": TaskType.CODE},
    {"id": "image", "task_preset": TaskPreset.CREATIVE, "task_type": TaskType.IMAGE},
    {"id": "music_sound", "task_preset": TaskPreset.CREATIVE, "task_type": TaskType.TEXT_GENERAL},
    {"id": "documents", "task_preset": TaskPreset.DOCUMENTS, "task_type": TaskType.TEXT_GENERAL},
    {"id": "translation", "task_preset": TaskPreset.TRANSLATION, "task_type": TaskType.TEXT_GENERAL},
    {"id": "reasoning", "task_preset": TaskPreset.REASONING, "task_type": TaskType.TEXT_REASONING},
]


__all__ = [
    "ANTISPAM",
    "CRYPTO_ASSETS",
    "CRYPTO_RATE_TTL_S",
    "FREE_TIER_PROVIDERS",
    "MODEL_REGISTRY",
    "MOOD_PROMPTS",
    "PAID_TIER_PROVIDERS",
    "PLAN_DURATIONS",
    "PLAN_FEATURES",
    "PLAN_LIMITS",
    "PLAN_PRICES_USD",
    "PLAN_PROVIDER_ACCESS",
    "PROMO_DISCOUNT_MAX",
    "PROMO_DISCOUNT_MIN",
    "PROVIDERS",
    "REFERRAL_PROMO_THRESHOLD",
    "REFERRAL_REWARD_DURATION_DIVIDER",
    "REFERRAL_REWARD_TEXT_REQUESTS",
    "SPEED_TAG_MAP",
    "STARS_PER_USD",
    "TASK_PROMPTS",
    "TRIALS",
    "USER_PROMO_DISCOUNT_MAX",
    "USER_PROMO_DISCOUNT_MIN",
    "WORK_CATEGORIES",
    "Mood",
    "Plan",
    "Settings",
    "SpeedMode",
    "StageMode",
    "TaskPreset",
    "TaskType",
    "get_settings",
    "settings",
    "shared_path",
]
