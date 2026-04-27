from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from core.i18n import t
from settings import (
    PLAN_DURATIONS,
    PLAN_FEATURES,
    PLAN_PRICES_STARS,
    WORK_CATEGORIES,
    Mood,
    Plan,
    SpeedMode,
    StageMode,
)


def file_format_kb(lang: str, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="MD", callback_data=f"{prefix}:md"),
            InlineKeyboardButton(text="TXT", callback_data=f"{prefix}:txt"),
            InlineKeyboardButton(text="DOCX", callback_data=f"{prefix}:docx"),
            InlineKeyboardButton(text="PDF", callback_data=f"{prefix}:pdf"),
        ],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_kb(
    lang: str,
    with_referrals: bool = True,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=t(lang, "menu.start_work"))],
        [KeyboardButton(text=t(lang, "menu.coursework")), KeyboardButton(text=t(lang, "menu.file_answer"))],
        [KeyboardButton(text=t(lang, "menu.upgrade")), KeyboardButton(text=t(lang, "menu.account"))],
        [KeyboardButton(text=t(lang, "menu.settings")), KeyboardButton(text=t(lang, "menu.help"))],
    ]
    if with_referrals:
        rows.append([KeyboardButton(text=t(lang, "menu.referrals"))])
    if is_admin:
        rows.append([KeyboardButton(text=t(lang, "menu.admin"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def categories_kb(lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for c in WORK_CATEGORIES:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, f"work.cat.{c['id']}"),
                    callback_data=f"cat:{c['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chats_kb(lang: str, category: str, chats: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for cid, title in chats:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"chat:open:{cid}")])
    rows.append([InlineKeyboardButton(text=t(lang, "work.new_chat"), callback_data=f"chat:new:{category}")])
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:work")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_kb(lang: str, plan: Plan, current: dict[str, str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(text=t(lang, "settings.language") + ": " + ("RU" if lang == "ru" else "EN"), callback_data="set:lang"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "settings.mood") + ": " + t(lang, f"mood.{current.get('mood', Mood.SMART_FRIEND.value)}"),
                callback_data="set:mood",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "settings.speed") + ": " + t(lang, f"speed.{current.get('speed', SpeedMode.BALANCE.value)}"),
                callback_data="set:speed",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "settings.stage") + ": " + t(lang, f"stage.{current.get('stage', StageMode.ONE.value)}"),
                callback_data="set:stage",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t(lang, "settings.language.ru"), callback_data="lang:ru"),
            InlineKeyboardButton(text=t(lang, "settings.language.en"), callback_data="lang:en"),
        ],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mood_kb(lang: str, plan: Plan) -> InlineKeyboardMarkup:
    moods = PLAN_FEATURES[plan]["moods"]
    rows = [[InlineKeyboardButton(text=t(lang, f"mood.{m.value}"), callback_data=f"mood:{m.value}")] for m in moods]
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def speed_kb(lang: str, plan: Plan) -> InlineKeyboardMarkup:
    speeds = PLAN_FEATURES[plan]["speed_modes"]
    rows = [[InlineKeyboardButton(text=t(lang, f"speed.{s.value}"), callback_data=f"speed:{s.value}")] for s in speeds]
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stage_kb(lang: str, plan: Plan) -> InlineKeyboardMarkup:
    stages = PLAN_FEATURES[plan]["stages"]
    rows = [[InlineKeyboardButton(text=t(lang, f"stage.{s.value}"), callback_data=f"stage:{s.value}")] for s in stages]
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_kb(lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in (Plan.PLUS, Plan.PRO, Plan.MAX):
        stars = PLAN_PRICES_STARS.get(p, {}).get("1m", 0)
        label = f"{t(lang, f'plan.{p.value}')} — {stars}⭐/мес"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan:{p.value}")])
    rows.append([InlineKeyboardButton(text=t(lang, "buy.title"), callback_data="buy:packs")])
    rows.append([InlineKeyboardButton(text=t(lang, "billing.trial.title"), callback_data="trial:menu")])
    rows.append([InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def durations_kb(lang: str, plan: Plan) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    table = PLAN_PRICES_STARS.get(plan, {})
    for key in PLAN_DURATIONS:
        stars = table.get(key, 0)
        label = f"{key} — {stars}⭐"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"dur:{plan.value}:{key}")])
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:billing")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def methods_kb(lang: str, plan: Plan, duration_key: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "billing.method_stars"), callback_data=f"pay:stars:{plan.value}:{duration_key}")],
        [InlineKeyboardButton(text=t(lang, "billing.method_crypto"), callback_data=f"pay:crypto:{plan.value}:{duration_key}")],
        [InlineKeyboardButton(text=t(lang, "billing.method_manual"), callback_data="pay:manual")],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"plan:{plan.value}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def crypto_assets_kb(lang: str, plan: Plan, duration_key: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for asset in ("TON", "USDT", "BTC"):
        rows.append(
            [
                InlineKeyboardButton(
                    text=asset,
                    callback_data=f"pay:cryptox:{plan.value}:{duration_key}:{asset}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"dur:{plan.value}:{duration_key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trials_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Plus 3d — 1⭐", callback_data="trial:plus")],
        [InlineKeyboardButton(text="Pro 3d — 5⭐", callback_data="trial:pro")],
        [InlineKeyboardButton(text="Max 3d — 10⭐", callback_data="trial:max")],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="nav:billing")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_kb(lang: str, channels: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for username, link in channels:
        rows.append([InlineKeyboardButton(text=f"{t(lang, 'channels.subscribe')}: @{username}", url=link)])
    rows.append([InlineKeyboardButton(text=t(lang, "channels.check"), callback_data="channels:check")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "admin.stats"), callback_data="admin:stats")],
        [InlineKeyboardButton(text=t(lang, "admin.users"), callback_data="admin:users")],
        [InlineKeyboardButton(text=t(lang, "admin.broadcasts"), callback_data="admin:broadcast")],
        [InlineKeyboardButton(text=t(lang, "admin.channels"), callback_data="admin:channels")],
        [InlineKeyboardButton(text=t(lang, "admin.providers"), callback_data="admin:providers")],
        [InlineKeyboardButton(text=t(lang, "admin.promos"), callback_data="admin:promos")],
        [InlineKeyboardButton(text=t(lang, "admin.withdraw"), callback_data="admin:withdraw")],
        [InlineKeyboardButton(text=t(lang, "menu.main"), callback_data="nav:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
