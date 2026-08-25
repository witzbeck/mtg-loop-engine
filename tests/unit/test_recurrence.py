"""Unit contracts for check_recurrence and GameState.get_path.

Recurrence is the core distinction between a one-shot interaction and a loop.
get_path is the vocabulary of LoopRelevantState — not coverage padding.
"""

from __future__ import annotations

import pytest

from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    PermanentSpec,
    StateDimension,
)
from mtg_loop_engine.semantics.enums import ComparisonOp, LoopType, Zone
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import check_recurrence


def _witness(dimensions: list[StateDimension]) -> LoopWitness:
    return LoopWitness(
        id="recurrence-matrix",
        classification=Classification(
            essential_card_count=2,
            strict_two_card=True,
            loop_type=LoopType.ARBITRARY_REPEATABLE,
        ),
        essential_cards=[
            EssentialCardRef(oracle_id="a", name="A"),
            EssentialCardRef(oracle_id="b", name="B"),
        ],
        card_semantics=[
            CardSemantics(oracle_id="a", name="A"),
            CardSemantics(oracle_id="b", name="B"),
        ],
        initial_state=InitialStateSpec(),
        loop_actions=[ActionStep(op="noop")],
        relevant_state=LoopRelevantState(dimensions=dimensions),
    )


def _mana_states(before_c: int, after_c: int) -> tuple[GameState, GameState]:
    before = GameState.from_spec(InitialStateSpec(mana=ManaAmount(colorless=before_c)))
    after = GameState.from_spec(InitialStateSpec(mana=ManaAmount(colorless=after_c)))
    return before, after


@pytest.mark.parametrize(
    "before_c,after_c,value,expect_ok",
    [
        (1, 1, None, True),  # implicit EXACT: after == before
        (1, 2, None, False),
        (1, 5, 5, True),  # explicit expected
        (1, 4, 5, False),
    ],
    ids=["implicit-pass", "implicit-fail", "explicit-pass", "explicit-fail"],
)
def test_exact_recurrence(before_c, after_c, value, expect_ok):
    before, after = _mana_states(before_c, after_c)
    result = check_recurrence(
        before,
        after,
        _witness([StateDimension(path="mana.colorless", op=ComparisonOp.EXACT, value=value)]),
    )
    assert result.ok is expect_ok


@pytest.mark.parametrize(
    "before_c,after_c,floor,expect_ok",
    [
        (1, 1, None, True),  # unchanged
        (1, 3, None, True),  # growth
        (3, 1, None, False),  # regression vs before
        (2, 3, 5, False),  # below explicit floor (even if >= before)
        (2, 5, 4, True),  # above floor and before
        (5, 5, 5, True),  # equal floor
    ],
    ids=[
        "unchanged",
        "growth",
        "regress-before",
        "below-floor",
        "above-floor",
        "equal-floor",
    ],
)
def test_minimum_recurrence(before_c, after_c, floor, expect_ok):
    before, after = _mana_states(before_c, after_c)
    result = check_recurrence(
        before,
        after,
        _witness(
            [StateDimension(path="mana.colorless", op=ComparisonOp.MINIMUM, value=floor)]
        ),
    )
    assert result.ok is expect_ok


@pytest.mark.parametrize(
    "before_c,after_c,ceiling,expect_ok",
    [
        (3, 2, None, True),  # implicit: after <= before
        (3, 3, None, True),
        (3, 4, None, False),
        (1, 4, 5, True),  # below explicit ceiling
        (1, 5, 5, True),  # equal ceiling
        (1, 6, 5, False),  # above ceiling
    ],
    ids=[
        "implicit-below",
        "implicit-equal",
        "implicit-above",
        "explicit-below",
        "explicit-equal",
        "explicit-above",
    ],
)
def test_maximum_recurrence(before_c, after_c, ceiling, expect_ok):
    before, after = _mana_states(before_c, after_c)
    result = check_recurrence(
        before,
        after,
        _witness(
            [
                StateDimension(
                    path="mana.colorless", op=ComparisonOp.MAXIMUM, value=ceiling
                )
            ]
        ),
    )
    assert result.ok is expect_ok


def test_missing_path_fails_with_diagnostic():
    before, after = _mana_states(0, 0)
    result = check_recurrence(
        before,
        after,
        _witness(
            [
                StateDimension(
                    path="permanents.missing.zone",
                    op=ComparisonOp.EXACT,
                    value="battlefield",
                )
            ]
        ),
    )
    assert result.ok is False
    assert any("missing path" in d for d in result.details)


def _board() -> GameState:
    return GameState.from_spec(
        InitialStateSpec(
            mana=ManaAmount(white=1, blue=2, colorless=3, any_color=4),
            life_you=35,
            life_opponent=20,
            permanents=[
                PermanentSpec(
                    object_id="c1",
                    oracle_id="oracle:c1",
                    name="Creature",
                    is_creature=True,
                    tapped=True,
                    summoning_sick=True,
                    counters={"p1p1": 2},
                ),
                PermanentSpec(
                    object_id="a1",
                    oracle_id="oracle:a1",
                    name="Artifact",
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="t1",
                    oracle_id="token:t",
                    name="Token",
                    is_token=True,
                    is_creature=True,
                ),
            ],
            event_counters={"mana": 7},
        )
    )


@pytest.mark.parametrize(
    "path,expected",
    [
        ("mana.white", 1),
        ("mana.blue", 2),
        ("mana.colorless", 3),
        ("mana.any_color", 4),
        ("life.you", 35),
        ("life.opponent", 20),
        ("events.mana", 7),
        ("permanents.c1.zone", Zone.BATTLEFIELD.value),
        ("permanents.c1.tapped", True),
        ("permanents.c1.counters.p1p1", 2),
        ("permanents.c1.summoning_sick", True),
        ("permanents.c1.once_per_turn_used.ab", False),
        ("count.battlefield.creature_tokens", 1),
        ("count.battlefield.creatures", 2),
        ("count.battlefield.artifacts", 1),
    ],
)
def test_get_path_matrix(path, expected):
    state = _board()
    assert state.get_path(path) == expected


def test_get_path_once_per_turn_true_after_mark():
    state = _board()
    state.permanents["c1"].once_per_turn_used.add("ab")
    assert state.get_path("permanents.c1.once_per_turn_used.ab") is True


@pytest.mark.parametrize(
    "path",
    [
        "",
        "permanents.c1.unknown_attr",
        "count.battlefield.enchantments",
        "bogus.root",
    ],
)
def test_get_path_invalid_raises(path):
    with pytest.raises(KeyError):
        _board().get_path(path)
