"""Official Arena card-name localization used only for display."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from src import constants
from .translator import FALLBACK_LOCALE, get_locale, tr

logger = logging.getLogger(__name__)
ARENA_LOCALE_TABLES = {
    "en_US": "Localizations_enUS",
    "it_IT": "Localizations_itIT",
}


class CardNameResolver:
    """Resolve display names without changing canonical card identifiers."""

    def __init__(self, database_location: str | None = None):
        self.database_location = database_location or ""
        self._lock = RLock()
        self._loaded_signature: tuple[str, str] | None = None
        self._by_id: dict[str, str] = {}
        self._by_name: dict[str, str] = {}
        self._canonical_by_display: dict[str, str] = {}

    def configure(self, database_location: str | None) -> None:
        location = database_location or ""
        if location != self.database_location:
            with self._lock:
                self.database_location = location
                self._loaded_signature = None
                self._by_id.clear()
                self._by_name.clear()
                self._canonical_by_display.clear()

    def _roots(self) -> Iterable[Path]:
        if self.database_location:
            configured = Path(self.database_location)
            yield configured
            yield configured / constants.LOCAL_DOWNLOADS_DATA
        if os.name == "nt":
            program_files = os.environ.get("ProgramFiles")
            if program_files:
                arena = Path(program_files) / "Wizards of the Coast" / "MTGA" / "MTGA_Data"
                yield arena / constants.LOCAL_DOWNLOADS_DATA

    def _database_file(self) -> Path | None:
        candidates: list[Path] = []
        prefix = constants.LOCAL_DATA_FILE_PREFIX_DATABASE
        for root in self._roots():
            if root.is_file() and root.name.startswith(prefix):
                candidates.append(root)
            elif root.is_dir():
                candidates.extend(p for p in root.glob(f"{prefix}*") if p.is_file())
        return max(candidates, key=lambda path: path.stat().st_mtime, default=None)

    @staticmethod
    def _tables(connection: sqlite3.Connection) -> set[str]:
        return {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}

    def _ensure_loaded(self) -> None:
        locale = get_locale()
        # Card tables render many rows; avoid touching the filesystem for every
        # cell after the active locale/database pair has been loaded.
        if self._loaded_signature and self._loaded_signature[1] == locale:
            return
        database = self._database_file()
        signature = (str(database or ""), locale)
        if signature == self._loaded_signature:
            return
        with self._lock:
            if signature == self._loaded_signature:
                return
            self._by_id.clear()
            self._by_name.clear()
            self._canonical_by_display.clear()
            localized_table = ARENA_LOCALE_TABLES.get(locale)
            if database is None or locale == FALLBACK_LOCALE or not localized_table:
                self._loaded_signature = signature
                return
            try:
                connection = sqlite3.connect(
                    f"file:{database.as_posix()}?mode=ro", uri=True, timeout=5.0
                )
                try:
                    required = {"Cards", "Localizations_enUS", localized_table}
                    if not required.issubset(self._tables(connection)):
                        logger.info("Arena database has no localization table for %s", locale)
                        self._loaded_signature = signature
                        return
                    query = f"""
                        WITH en AS (
                            SELECT LocId, Loc, ROW_NUMBER() OVER (
                                PARTITION BY LocId ORDER BY Formatted
                            ) AS row_number
                            FROM Localizations_enUS
                        ), localized AS (
                            SELECT LocId, Loc, ROW_NUMBER() OVER (
                                PARTITION BY LocId ORDER BY Formatted
                            ) AS row_number
                            FROM {localized_table}
                        )
                        SELECT Cards.GrpId, en.Loc, localized.Loc
                        FROM Cards
                        JOIN en ON Cards.TitleId = en.LocId AND en.row_number = 1
                        JOIN localized ON Cards.TitleId = localized.LocId
                                      AND localized.row_number = 1
                        WHERE en.Loc IS NOT NULL AND localized.Loc IS NOT NULL
                    """
                    for grp_id, canonical, localized in connection.execute(query):
                        canonical, localized = str(canonical), str(localized)
                        self._by_id[str(grp_id)] = localized
                        self._by_name.setdefault(canonical, localized)
                        self._canonical_by_display.setdefault(localized, canonical)
                finally:
                    connection.close()
            except (OSError, sqlite3.Error) as error:
                logger.warning("Could not load Arena card localizations: %s", error)
            self._loaded_signature = signature

    def display_name(self, card: dict[str, Any] | str, arena_id: Any = None) -> str:
        self._ensure_loaded()
        if isinstance(card, dict):
            canonical = str(card.get(constants.DATA_FIELD_NAME, ""))
            arena_id = arena_id or card.get("arena_id") or card.get("grp_id")
        else:
            canonical = str(card or "")
        if arena_id is not None and str(arena_id) in self._by_id:
            return self._by_id[str(arena_id)]
        if canonical in self._by_name:
            return self._by_name[canonical]
        if " // " in canonical:
            faces = canonical.split(" // ")
            translated = [self._by_name.get(face, face) for face in faces]
            if translated != faces:
                return " // ".join(translated)
        return canonical

    def canonical_name(self, display_name: str) -> str:
        self._ensure_loaded()
        return self._canonical_by_display.get(display_name, display_name)


_resolver = CardNameResolver()


def configure_card_names(database_location: str | None) -> None:
    _resolver.configure(database_location)


def card_name(card: dict[str, Any] | str, arena_id: Any = None) -> str:
    return _resolver.display_name(card, arena_id)


def optimization_note(text: str) -> str:
    """Localize optimizer prose and its card names without mutating its result."""
    patterns = (
        (r"^Optimized: Curve Lower \(-(.+), \+(.+)\)$", "generated.optimize_curve"),
        (r"^Optimized: Power Up \(-(.+), \+(.+)\)$", "generated.optimize_power"),
        (r"^Optimized: Play 18 Lands \(-(.+)\)$", "generated.optimize_18"),
        (r"^Optimized: Play 16 Lands \(\+(.+)\)$", "generated.optimize_16"),
        (r"^Optimized: Fix Mana Base \(-(.+), \+Basic Land\)$", "generated.optimize_fix"),
        (r"^Optimized: Optimize Mana \(\+(.+), -(.+)\)$", "generated.optimize_mana"),
    )
    for pattern, key in patterns:
        match = re.match(pattern, text)
        if match:
            names = [card_name(value) for value in match.groups()]
            params = {"cut": names[0]}
            if len(names) > 1:
                params["add"] = names[1]
            return tr(key, **params)
    return text
