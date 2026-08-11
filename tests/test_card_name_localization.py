import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.i18n import CardNameResolver, set_locale


class CardNameResolverTests(unittest.TestCase):
    def setUp(self):
        set_locale("it_IT")
        self.directory = tempfile.TemporaryDirectory()
        raw = Path(self.directory.name) / "Downloads" / "Raw"
        raw.mkdir(parents=True)
        self.database = raw / "Raw_CardDatabase_test.sqlite"
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE Cards (GrpId INT, TitleId INT, LinkedFaceGrpIds TEXT);
            CREATE TABLE Localizations_enUS (LocId INT, Formatted INT, Loc TEXT);
            CREATE TABLE Localizations_itIT (LocId INT, Formatted INT, Loc TEXT);
            """
        )
        cards = [(1, 10, "2"), (2, 11, "1"), (3, 12, ""), (4, 12, "")]
        english = [
            (10, 0, "Daybound Hero"),
            (11, 0, "Nightbound Hero"),
            (12, 0, "Collector's Café"),
        ]
        italian = [
            (10, 0, "Eroe del Giorno"),
            (11, 0, "Eroe della Notte"),
            (12, 0, "Caffè del Collezionista"),
        ]
        connection.executemany("INSERT INTO Cards VALUES (?, ?, ?)", cards)
        connection.executemany("INSERT INTO Localizations_enUS VALUES (?, ?, ?)", english)
        connection.executemany("INSERT INTO Localizations_itIT VALUES (?, ?, ?)", italian)
        connection.commit()
        connection.close()
        self.resolver = CardNameResolver(self.directory.name)

    def tearDown(self):
        set_locale("it_IT")
        self.directory.cleanup()

    def test_official_italian_name_and_arena_id(self):
        self.assertEqual(self.resolver.display_name("Daybound Hero", 1), "Eroe del Giorno")

    def test_missing_translation_falls_back_to_english(self):
        self.assertEqual(self.resolver.display_name("Digital Only Card"), "Digital Only Card")

    def test_double_faced_card(self):
        self.assertEqual(
            self.resolver.display_name("Daybound Hero // Nightbound Hero"),
            "Eroe del Giorno // Eroe della Notte",
        )

    def test_multiple_arena_ids_reprints_accents_and_apostrophes(self):
        self.assertEqual(self.resolver.display_name("Collector's Café", 3), "Caffè del Collezionista")
        self.assertEqual(self.resolver.display_name("Collector's Café", 4), "Caffè del Collezionista")

    def test_english_locale_preserves_canonical_name(self):
        set_locale("en_US")
        self.assertEqual(self.resolver.display_name("Daybound Hero", 1), "Daybound Hero")


if __name__ == "__main__":
    unittest.main()
