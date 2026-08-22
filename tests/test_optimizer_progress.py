from unittest.mock import MagicMock, patch

import pytest

from src.card_logic import clear_deck_cache, optimize_deck, suggest_deck
from src.advisor.mana_base import brute_force_mana_base
from src.advisor.progress import emit_progress
from src.advisor.simulator import simulate_deck
from src.ui.windows.custom_deck import CustomDeckPanel


def _stats():
    return {
        "cast_t2": 50.0,
        "cast_t3": 50.0,
        "cast_t4": 50.0,
        "curve_out": 10.0,
        "mulligans": 5.0,
        "screw_t3": 10.0,
        "screw_t4": 10.0,
        "color_screw_t3": 5.0,
        "flood_t5": 10.0,
        "removal_t4": 20.0,
        "avg_hand_size": 6.8,
    }


def _fake_simulator(
    deck,
    iterations=10000,
    progress_callback=None,
    *,
    phase="monte_carlo",
    detail=None,
    progress_context=None,
):
    emit_progress(
        progress_callback,
        phase,
        0,
        iterations,
        detail=detail,
        context=progress_context,
    )
    emit_progress(
        progress_callback,
        phase,
        iterations,
        iterations,
        detail=detail,
        context=progress_context,
    )
    return _stats()


def _legal_deck():
    return [
        {
            "name": "Forest",
            "types": ["Land", "Basic"],
            "count": 17,
            "colors": ["G"],
        },
        {
            "name": "Bear",
            "types": ["Creature"],
            "count": 23,
            "mana_cost": "{1}{G}",
            "cmc": 2,
            "deck_colors": {"All Decks": {"gihwr": 55.0}},
        },
    ]


def test_simulate_deck_reports_real_batched_progress_and_preserves_result():
    arrays = tuple(object() for _ in range(6))

    def deterministic_kernel(*args):
        iterations = args[-1]
        return tuple(iterations * (index + 1) for index in range(11))

    updates = []
    with (
        patch("src.advisor.simulator._parse_deck_to_arrays", return_value=arrays),
        patch(
            "src.advisor.simulator._run_fast_monte_carlo",
            side_effect=deterministic_kernel,
        ),
    ):
        original = simulate_deck([], iterations=1000)
        with_progress = simulate_deck(
            [],
            iterations=1000,
            progress_callback=updates.append,
        )

    assert with_progress == original
    assert updates[0]["current"] == 0
    assert updates[-1]["current"] == 1000
    assert updates[-1]["total"] == 1000
    assert len(updates) <= 21


def test_optimizer_reports_variants_final_simulation_and_completion():
    updates = []
    with patch(
        "src.advisor.deck_builder.simulate_deck",
        side_effect=_fake_simulator,
    ) as mocked_simulator:
        result = optimize_deck(
            _legal_deck(),
            [],
            "G",
            ["G"],
            progress_callback=updates.append,
        )

    phases = [event["phase"] for event in updates]
    variant_start = next(
        event
        for event in updates
        if event["phase"] == "deck_variants" and event["current"] == 0
    )
    assert phases[0] == "preparing"
    assert variant_start["total"] == mocked_simulator.call_count - 1
    assert "variant_simulation" in phases
    assert "final_simulation" in phases
    assert updates[-1]["phase"] == "completed"
    assert updates[-1]["current"] == updates[-1]["total"] == 10000
    assert result[2] == _stats()


def test_optimizer_result_is_identical_with_optional_callback():
    with patch(
        "src.advisor.deck_builder.simulate_deck",
        side_effect=_fake_simulator,
    ):
        without_progress = optimize_deck(_legal_deck(), [], "G", ["G"])
        with_progress = optimize_deck(
            _legal_deck(), [], "G", ["G"], progress_callback=lambda event: None
        )

    assert with_progress == without_progress


def test_suggestion_generation_reports_exact_variant_count():
    updates = []
    deck = _legal_deck()
    clear_deck_cache()
    with (
        patch("src.advisor.deck_builder.identify_top_pairs", return_value=[["G"]]),
        patch("src.advisor.deck_builder.build_variant_consistency", return_value=deck),
        patch("src.advisor.deck_builder.build_variant_greedy", return_value=(deck, "R")),
        patch("src.advisor.deck_builder.build_variant_curve", return_value=deck),
        patch("src.advisor.deck_builder.build_variant_soup", return_value=(deck, ["G"])),
        patch("src.advisor.deck_builder.get_sideboard", return_value=[]),
        patch(
            "src.advisor.deck_builder.calculate_holistic_score",
            return_value=(100.0, ""),
        ),
        patch("src.advisor.deck_builder.simulate_deck", side_effect=_fake_simulator),
    ):
        suggest_deck(
            [{"name": f"Spell {index}", "types": ["Creature"]} for index in range(23)],
            MagicMock(),
            MagicMock(),
            progress_callback=updates.append,
            dataset_name="progress-test",
        )
    clear_deck_cache()

    start = next(
        event
        for event in updates
        if event.get("phase") == "deck_variants" and event.get("current") == 0
    )
    assert start["total"] == 4
    assert updates[-1]["phase"] == "completed"
    assert updates[-1]["current"] == updates[-1]["total"] == 4


def test_mana_optimizer_reports_actual_generated_configuration_total():
    baseline = [
        {"name": "Mountain", "types": ["Land", "Basic"], "colors": ["R"]},
        {"name": "Mountain", "types": ["Land", "Basic"], "colors": ["R"]},
        {"name": "Forest", "types": ["Land", "Basic"], "colors": ["G"]},
        {"name": "Forest", "types": ["Land", "Basic"], "colors": ["G"]},
    ]
    updates = []
    with (
        patch(
            "src.advisor.mana_base.calculate_dynamic_mana_base",
            return_value=baseline,
        ),
        patch("src.advisor.simulator.simulate_deck", side_effect=_fake_simulator),
    ):
        brute_force_mana_base(
            [{"name": "Spell", "types": ["Creature"]}] * 36,
            [],
            ["R", "G"],
            forced_count=4,
            progress_callback=updates.append,
        )

    configuration_events = [
        event for event in updates if event["phase"] == "mana_optimization"
    ]
    # All five legal splits from 0/4 through 4/0 are really simulated.
    assert configuration_events[0]["total"] == 5
    assert configuration_events[-1]["current"] == 5
    assert configuration_events[-1]["total"] == 5


def test_optimizer_emits_error_and_reraises():
    updates = []
    with patch(
        "src.advisor.deck_builder.simulate_deck",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            optimize_deck(
                _legal_deck(),
                [],
                "G",
                ["G"],
                progress_callback=updates.append,
            )

    assert updates[-1]["phase"] == "error"


def test_worker_progress_is_queued_before_any_ui_update():
    panel = MagicMock()
    event = {"phase": "final_simulation", "current": 50, "total": 100}

    CustomDeckPanel._queue_optimizer_progress(panel, 7, event)

    panel._apply_optimizer_progress.assert_not_called()
    callback = panel.after.call_args.args[1]
    callback()
    panel._apply_optimizer_progress.assert_called_once_with(7, event)
