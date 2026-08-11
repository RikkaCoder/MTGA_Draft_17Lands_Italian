"""Public localization helpers used by the presentation layer."""

from .translator import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    available_locales,
    column_label,
    color_label,
    format_number,
    format_percent,
    get_locale,
    set_locale,
    tag_label,
    type_label,
    type_list_label,
    tr,
    translate_generated,
)
from .card_names import CardNameResolver, card_name, configure_card_names, optimization_note

__all__ = [
    "DEFAULT_LOCALE",
    "FALLBACK_LOCALE",
    "CardNameResolver",
    "available_locales",
    "column_label",
    "color_label",
    "card_name",
    "configure_card_names",
    "format_number",
    "format_percent",
    "get_locale",
    "optimization_note",
    "set_locale",
    "tag_label",
    "type_label",
    "type_list_label",
    "tr",
    "translate_generated",
]
