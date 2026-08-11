import unittest
from unittest.mock import MagicMock

from src.advisor.engine import DraftAdvisor
from src.advisor.deck_builder import deck_identity_colors, select_safe_deck_index
from src.advisor.mana_base import calculate_dynamic_mana_base
from src.card_logic import get_card_colors, get_deck_metrics
from src.i18n import set_locale, translate_generated
from src.signals import SignalCalculator


class StrategicLocalizationRegressionTests(unittest.TestCase):
    @staticmethod
    def _evaluate(locale):
        set_locale(locale)
        metrics = MagicMock()
        metrics.format_texture = {"G": {"2-drop": 10, "removal": 10}}
        metrics.get_metrics.return_value = (55.0, 4.0)
        pool = [
            {
                "name": "Canonical Bear",
                "colors": ["G"],
                "types": ["Creature"],
                "cmc": 2,
                "deck_colors": {"All Decks": {"gihwr": 55.0}},
            }
        ] * 10
        pack = [
            {
                "name": "Canonical Bomb",
                "colors": ["G"],
                "types": ["Creature"],
                "cmc": 4,
                "deck_colors": {"All Decks": {"gihwr": 75.0, "iwd": 5.0, "alsa": 2.0}},
            },
            {
                "name": "Canonical Filler",
                "colors": ["G"],
                "types": ["Creature"],
                "cmc": 2,
                "deck_colors": {"All Decks": {"gihwr": 50.0, "iwd": 1.0, "alsa": 4.0}},
            },
            {
                "name": "Canonical Medium",
                "colors": ["G"],
                "types": ["Creature"],
                "cmc": 3,
                "deck_colors": {"All Decks": {"gihwr": 55.0, "iwd": 1.0, "alsa": 3.0}},
            },
        ]
        recommendations = DraftAdvisor(metrics, pool).evaluate_pack(pack, current_pick=1)
        return [
            (
                item.card_name,
                item.contextual_score,
                item.cast_probability,
                item.wheel_chance,
                item.archetype_fit,
                tuple(item.reasoning),
            )
            for item in recommendations
        ]

    def tearDown(self):
        set_locale("it_IT")

    def test_locale_does_not_change_recommendation_order_or_scores(self):
        self.assertEqual(self._evaluate("en_US"), self._evaluate("it_IT"))

    def test_translation_is_applied_only_after_strategy(self):
        raw = self._evaluate("it_IT")
        translated = [translate_generated(reason) for reason in raw[0][-1]]
        self.assertEqual(raw[0][0], "Canonical Bomb")
        self.assertNotEqual(translated, list(raw[0][-1]))

    @staticmethod
    def _mechanics_snapshot(locale):
        set_locale(locale)
        metrics = MagicMock()
        metrics.get_metrics.return_value = (54.0, 4.0)
        spells = [
            {
                "name": "Green Two Drop",
                "colors": ["G"],
                "types": ["Creature"],
                "mana_cost": "{1}{G}",
                "cmc": 2,
                "deck_colors": {"All Decks": {"gihwr": 58.0, "ata": 3.0}},
            },
            {
                "name": "Blue Spell",
                "colors": ["U"],
                "types": ["Instant"],
                "mana_cost": "{U}{U}",
                "cmc": 2,
                "deck_colors": {"All Decks": {"gihwr": 56.0, "ata": 4.0}},
            },
        ]
        advisor = DraftAdvisor(metrics, spells)
        lands = calculate_dynamic_mana_base(spells, [], ["G", "U"])
        signals = SignalCalculator(metrics).calculate_pack_signals(spells, 8)
        deck = spells + lands
        metrics_result = get_deck_metrics(deck)
        greedy = {
            "deck": deck,
            "colors": ["G", "U", "R"],
            "identity_colors": ["G", "U", "R"],
            "rating": 10,
            "breakdown": "",
        }
        consistent = {
            "deck": deck,
            "colors": ["G", "U"],
            "identity_colors": ["G", "U"],
            "rating": 9,
            "breakdown": "",
        }
        variants = [("Greedy", greedy), ("Consistent", consistent)]
        return {
            "colors": get_card_colors("{2}{G}{U/U}"),
            "archetype": advisor.main_archetype,
            "mana_base": tuple(card["name"] for card in lands),
            "statistics": metrics_result,
            "signals": signals,
            "deck_identity": deck_identity_colors(consistent),
            "safe_deck_index": select_safe_deck_index(variants),
        }

    def test_locale_does_not_change_colors_archetype_deck_mana_stats_or_signals(self):
        self.assertEqual(
            self._mechanics_snapshot("en_US"),
            self._mechanics_snapshot("it_IT"),
        )


if __name__ == "__main__":
    unittest.main()
