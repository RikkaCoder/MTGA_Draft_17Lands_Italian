"""Small JSON-backed localization service."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_LOCALE = "it_IT"
FALLBACK_LOCALE = "en_US"
LOCALES_DIR = Path(__file__).with_name("locales")

logger = logging.getLogger(__name__)
_lock = RLock()
_catalogs: dict[str, dict[str, Any]] = {}
_locale = DEFAULT_LOCALE
_reported_missing: set[tuple[str, str]] = set()


def _load(locale: str) -> dict[str, Any]:
    with _lock:
        if locale not in _catalogs:
            path = LOCALES_DIR / f"{locale}.json"
            try:
                with path.open("r", encoding="utf-8") as stream:
                    value = json.load(stream)
                _catalogs[locale] = value if isinstance(value, dict) else {}
            except (OSError, json.JSONDecodeError) as error:
                logger.error("Could not load locale %s: %s", locale, error)
                _catalogs[locale] = {}
        return _catalogs[locale]


def _lookup(catalog: dict[str, Any], key: str) -> Any:
    value: Any = catalog
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def available_locales() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in LOCALES_DIR.glob("*.json")))


def set_locale(locale: str | None) -> str:
    """Select a locale, safely falling back when it is unknown."""
    global _locale
    requested = str(locale or DEFAULT_LOCALE)
    _locale = requested if requested in available_locales() else FALLBACK_LOCALE
    _load(FALLBACK_LOCALE)
    _load(_locale)
    return _locale


def get_locale() -> str:
    return _locale


def tr(key: str, *, count: int | float | None = None, **params: Any) -> str:
    """Translate a key with English fallback, plurals and safe formatting."""
    value = _lookup(_load(_locale), key)
    if value is None and _locale != FALLBACK_LOCALE:
        value = _lookup(_load(FALLBACK_LOCALE), key)
    if value is None:
        marker = (_locale, key)
        if marker not in _reported_missing:
            _reported_missing.add(marker)
            logger.warning("Missing translation key '%s' for locale %s", key, _locale)
        value = key
    if isinstance(value, dict):
        plural_key = "one" if count == 1 else "other"
        value = value.get(plural_key, value.get("other", key))
    values = dict(params)
    if count is not None:
        values.setdefault("count", count)
    try:
        return str(value).format(**values)
    except (KeyError, ValueError, IndexError) as error:
        logger.warning("Could not format translation key '%s': %s", key, error)
        return str(value)


def format_number(value: int | float, decimals: int | None = None) -> str:
    rendered = f"{value:,}" if decimals is None else f"{value:,.{decimals}f}"
    if _locale == "it_IT":
        rendered = rendered.translate(str.maketrans({",": ".", ".": ","}))
    return rendered


def format_percent(value: int | float, decimals: int = 1) -> str:
    return f"{format_number(value, decimals)}%"


_GENERATED_EXACT_KEYS = {
    "LATE SIGNAL": "advisor.late_signal",
    "Off-Color": "advisor.off_color",
    "Off-Color Gold": "generated.off_color_gold",
    "Uncastable (Double Pip)": "generated.uncastable_double_pip",
    "Bomb Splash": "generated.bomb_splash",
    "Premium Removal Splash": "generated.removal_splash",
    "Greedy Bomb Splash": "generated.greedy_bomb_splash",
    "Splashable": "generated.splashable",
    "This is the only available option.": "generated.only_option",
    "Basic Land (Skip)": "generated.basic_land_skip",
    "TRUE BOMB (High IWD)": "generated.true_bomb",
    "Excellent Aggro Curve (+5.0)": "generated.aggro_curve",
    "Rock-Solid Mana (+2.5)": "generated.solid_mana",
    "Supported Domain/Soup (+6.0)": "generated.supported_domain",
    "Lacks Evasion/Reach (-5.0)": "generated.lacks_evasion",
}

_GENERATED_PATTERNS = (
    (re.compile(r"^Archetype Glue \(\+(?P<value>.+)\)$"), "generated.archetype_glue"),
    (re.compile(r"^Archetype Synergy \(\+(?P<value>.+)\)$"), "generated.archetype_synergy"),
    (re.compile(r"^Improves Best Deck \(\+(?P<value>.+)\)$"), "generated.improves_deck"),
    (re.compile(r"^Wheels ~(?P<value>.+)$"), "generated.wheels"),
    (re.compile(r"^Highly Replaceable (?P<role>.+)$"), "generated.replaceable"),
    (re.compile(r"^High Curve / Needs Lands \(-(?P<value>.+)\)$"), "generated.needs_lands"),
    (re.compile(r"^Greedy Mana Strain \(-(?P<value>.+)\)$"), "generated.mana_strain"),
    (re.compile(r"^Incomplete Deck \(-(?P<value>.+)\)$"), "generated.incomplete_deck"),
    (re.compile(r"^Color Screw \(-(?P<value>.+)\)$"), "generated.color_screw"),
    (re.compile(r"^Mana Screw \(-(?P<value>.+)\)$"), "generated.mana_screw"),
    (re.compile(r"^Flood Risk \(-(?P<value>.+)\)$"), "generated.flood_risk"),
    (re.compile(r"^High VOR: Scarce (?P<color>[WUBRG]) (?P<role>.+) \(\+(?P<value>.+)\)$"), "generated.high_vor"),
    (re.compile(r"^(?P<tribe>.+) Synergy \(\+(?P<value>.+)\)$"), "generated.tribal_synergy"),
    (re.compile(r"^Analyzing (?P<archetype>.+) Archetypes\.\.\.$"), "generated.analyzing_archetypes"),
)


def translate_generated(text: str) -> str:
    """Localize a message emitted by strategic code without changing that code."""
    if text in _GENERATED_EXACT_KEYS:
        return tr(_GENERATED_EXACT_KEYS[text])
    if text == "Loaded optimized decks from cache.":
        return tr("generated.loaded_cache")
    if text == "Analyzing Domain / Soup...":
        return tr("generated.analyzing_soup")
    if text.startswith("Optimized: "):
        return tr("generated.optimized", description=text.removeprefix("Optimized: "))
    deck_label = re.match(
        r"^(?P<archetype>\S+) (?P<variant>.+) \[Est: (?P<record>[^]]+)] "
        r"\(Power: (?P<power>[^)]+)\)$",
        text,
    )
    if deck_label:
        values = deck_label.groupdict()
        variant = values.pop("variant")
        if variant == "Consistent":
            variant = tr("generated.consistent")
        elif variant == "Good Stuff (Soup)":
            variant = tr("generated.good_stuff")
        elif variant.startswith("Splash "):
            variant = tr("generated.splash_variant", color=color_label(variant[7:]))
        return tr("generated.deck_label", variant=variant, **values)
    for pattern, key in _GENERATED_PATTERNS:
        match = pattern.match(text)
        if match:
            values = match.groupdict()
            role_keys = {
                "2-Drops": "roles.early_play",
                "Removal": "roles.removal",
                "Evasion": "roles.evasion",
            }
            if values.get("role") in role_keys:
                values["role"] = tr(role_keys[values["role"]])
            if "color" in values:
                values["color"] = color_label(values["color"])
            return tr(key, **values)
    return text


def column_label(field: str, *, full: bool = False) -> str:
    """Return a localized table heading while preserving the field identifier."""
    normalized = str(field).lower()
    labels = {
        "name": "stats.name",
        "gihwr": "stats.gihwr",
        "ohwr": "stats.ohwr",
        "gpwr": "stats.gpwr",
        "gnswr": "stats.gnswr",
        "gdwr": "stats.gdwr",
        "alsa": "stats.alsa",
        "ata": "stats.ata",
        "iwd": "stats.iwd",
        "wheel": "stats.wheel",
        "colors": "stats.colors",
        "count": "stats.count",
        "value": "stats.value",
        "tags": "stats.tags",
        "cmc": "stats.cmc",
        "types": "stats.types",
        "mana_cost": "stats.mana_cost",
        "set": "table.set",
        "event": "table.event",
        "group": "table.group",
        "start": "table.start",
        "end": "table.end",
        "collected": "table.collected",
        "games": "table.games",
        "label": "table.label",
        "date": "table.date",
    }
    if normalized not in labels:
        return str(field).upper()
    label = tr(labels[normalized])
    return label if full else label.split("(")[0].strip().rstrip(":")


def tag_label(tag: str) -> str:
    icons = {
        "removal": "🎯",
        "evasion": "🦅",
        "card_advantage": "📚",
        "fixing_ramp": "🌈",
        "fixing": "🌈",
        "combat_trick": "⚔️",
        "enhancement": "🛡️",
        "token_maker": "👯",
        "lifegain": "💖",
        "mana_sink": "⚙️",
        "protection": "🛡️",
        "hate": "🚫",
    }
    key = f"tags.{tag}"
    label = tr(key)
    if label == key:
        label = tag.replace("_", " ").capitalize()
    return f"{icons.get(tag, '')} {label}".strip()


def color_label(value: str) -> str:
    key = str(value).replace(" ", "").upper()
    return tr(f"colors.{key}") if key in {
        "W", "U", "B", "R", "G", "C", "M", "NC",
        "WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG",
    } else value


def type_label(value: str) -> str:
    key = str(value).lower().replace("/", "_").replace(" ", "_")
    translated = tr(f"types.{key}")
    return value if translated == f"types.{key}" else translated


def type_list_label(values: list[str] | tuple[str, ...] | str) -> str:
    """Localize a card type list that is already safe for presentation."""
    if isinstance(values, str):
        values = values.split()
    return " ".join(type_label(value) for value in values)


set_locale(DEFAULT_LOCALE)
