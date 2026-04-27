from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from bot.config.settings import PROJECT_ROOT, settings

LOCALE_DIR = PROJECT_ROOT / "bot" / "locale"
SUPPORTED = ("ru", "en")


@lru_cache(maxsize=8)
def _load(lang: str) -> dict[str, str]:
    path: Path = LOCALE_DIR / lang / "messages.json"
    if not path.exists():
        path = LOCALE_DIR / settings.DEFAULT_LANGUAGE / "messages.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize(lang: str | None) -> str:
    if not lang:
        return settings.DEFAULT_LANGUAGE
    lang = lang.lower()[:2]
    return lang if lang in SUPPORTED else settings.DEFAULT_LANGUAGE


def t(lang: str | None, key: str, **kwargs: object) -> str:
    catalog = _load(normalize(lang))
    template = catalog.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
