import tkinter
import unittest
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.configuration import Configuration
from src.i18n import set_locale, tr
from src.ui.windows.compare import ComparePanel
from src.ui.windows.custom_deck import CustomDeckPanel
from src.ui.windows.overlay import CompactOverlay


class ItalianUiSmokeTests(unittest.TestCase):
    def setUp(self):
        set_locale("it_IT")
        self.root = tkinter.Tk()
        self.root.withdraw()

    def tearDown(self):
        for child in self.root.winfo_children():
            child.destroy()
        set_locale("it_IT")

    def _draft(self):
        draft = MagicMock()
        draft.set_data.get_card_ratings.return_value = {}
        draft.retrieve_taken_cards.return_value = []
        draft.retrieve_set_metrics.return_value = MagicMock()
        draft.retrieve_tier_data.return_value = {}
        return draft

    def test_compare_and_deck_builder_load_in_italian(self):
        compare = ComparePanel(self.root, self._draft(), Configuration())
        custom = CustomDeckPanel(
            self.root, self._draft(), Configuration(), MagicMock()
        )

        compare_texts = [
            child.cget("text")
            for child in compare.winfo_children()[0].winfo_children()
            if "text" in child.keys()
        ]
        self.assertIn(tr("compare.search"), compare_texts)
        self.assertIn(tr("compare.add"), compare_texts)
        self.assertEqual(
            custom.notebook.tab(custom.builder_tab, "text").strip(),
            tr("deck.builder"),
        )

    @patch("tkinter.Toplevel.overrideredirect")
    @patch("tkinter.Toplevel.wm_overrideredirect")
    def test_mini_mode_loads_in_italian(self, _wm, _override):
        context = MagicMock()
        context.orchestrator.scanner.retrieve_current_limited_event.return_value = (
            "M10", "Draft"
        )
        context.vars = {
            "selected_event": MagicMock(get=lambda: "PremierDraft"),
            "selected_group": MagicMock(get=lambda: "All"),
            "deck_filter": MagicMock(get=lambda: "All Decks"),
        }
        overlay = CompactOverlay(
            self.root, context, Configuration(), lambda: None
        )
        self.assertEqual(overlay.title(), tr("overlay.title"))
        overlay.destroy()


class LocalizedSourceTests(unittest.TestCase):
    def test_primary_user_messages_are_not_hardcoded(self):
        forbidden = {
            "Generate a deck first.",
            "Deck has fewer than 7 cards.",
            "Generate a deck to analyze.",
            "Generate a deck to run simulations.",
        }
        paths = (
            "src/ui/windows/suggest_deck.py",
            "src/ui/windows/custom_deck.py",
            "src/ui/windows/compare.py",
            "src/ui/windows/overlay.py",
        )
        for path in paths:
            with open(path, encoding="utf-8") as stream:
                source = stream.read()
            for message in forbidden:
                self.assertNotIn(message, source, f"{message!r} remains in {path}")

    def test_widget_and_dialog_literals_are_centralized(self):
        offenders = []
        for path in Path("src/ui").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for keyword in node.keywords:
                    value = keyword.value
                    if (
                        keyword.arg in {"text", "title", "label", "message"}
                        and isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and any(char.isalpha() for char in value.value)
                    ):
                        offenders.append((str(path), node.lineno, value.value))
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr
                    in {"showerror", "showwarning", "showinfo", "askyesno", "askokcancel"}
                ):
                    for value in node.args[:2]:
                        if (
                            isinstance(value, ast.Constant)
                            and isinstance(value.value, str)
                            and any(char.isalpha() for char in value.value)
                        ):
                            offenders.append((str(path), node.lineno, value.value))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
