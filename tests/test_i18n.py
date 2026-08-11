import json
import logging
import tempfile
import unittest
from pathlib import Path

from src.configuration import Configuration, read_configuration, write_configuration
from src.i18n import (
    format_number,
    get_locale,
    set_locale,
    tr,
    translate_generated,
    optimization_note,
)


class TranslatorTests(unittest.TestCase):
    def setUp(self):
        set_locale("it_IT")

    def tearDown(self):
        set_locale("it_IT")

    def test_italian_is_default(self):
        set_locale("it_IT")
        self.assertEqual(get_locale(), "it_IT")
        self.assertEqual(tr("settings.title"), "Preferenze")

    def test_english_can_be_selected(self):
        set_locale("en_US")
        self.assertEqual(tr("settings.title"), "Preferences")

    def test_unknown_locale_falls_back_to_english(self):
        set_locale("not-a-locale")
        self.assertEqual(get_locale(), "en_US")
        self.assertEqual(tr("settings.title"), "Preferences")

    def test_missing_italian_key_falls_back_to_english(self):
        # This key is deliberately injected in the cached English catalog only,
        # keeping production locale files complete.
        import src.i18n.translator as translator

        translator._load("en_US")["test_fallback"] = "English fallback"
        with self.assertLogs("src.i18n.translator", level=logging.WARNING):
            self.assertEqual(tr("test_fallback.missing"), "test_fallback.missing")
        translator._load("en_US")["test_fallback"] = {"value": "English fallback"}
        self.assertEqual(tr("test_fallback.value"), "English fallback")

    def test_missing_key_does_not_crash(self):
        self.assertEqual(tr("missing.example.key"), "missing.example.key")

    def test_dynamic_parameters_multiline_plural_and_numbers(self):
        self.assertEqual(tr("app.version", version="9.9"), "Versione 9.9")
        self.assertEqual(tr("plural.cards", count=1), "1 carta")
        self.assertEqual(tr("plural.cards", count=3), "3 carte")
        self.assertEqual(format_number(1234.5, 1), "1.234,5")
        self.assertIn("\n", tr("errors.startup", message="boom"))

    def test_generated_reason_is_localized_without_mutation(self):
        original = "Mana Screw (-3.2)"
        self.assertEqual(translate_generated(original), "Carenza di mana (-3.2)")
        self.assertEqual(original, "Mana Screw (-3.2)")

    def test_dynamic_deck_builder_messages_are_localized(self):
        self.assertEqual(
            translate_generated("Analyzing BG Archetypes..."),
            "Analisi degli archetipi BG...",
        )
        self.assertEqual(
            optimization_note("Optimized: Play 18 Lands (-Canonical Cut)"),
            "Ottimizzato: gioca 18 terre (-Canonical Cut)",
        )


class ConfigurationLanguageTests(unittest.TestCase):
    def test_legacy_configuration_gets_italian_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"settings": {"theme": "Dark"}}), encoding="utf-8")
            config, success = read_configuration(str(path))
            self.assertTrue(success)
            self.assertEqual(config.settings.language, "it_IT")

    def test_language_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = Configuration()
            config.settings.language = "en_US"
            self.assertTrue(write_configuration(config, str(path)))
            loaded, success = read_configuration(str(path))
            self.assertTrue(success)
            self.assertEqual(loaded.settings.language, "en_US")


if __name__ == "__main__":
    unittest.main()
