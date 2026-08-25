"""Fail-closed StateDimension path grammar contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    OutputDelta,
    PermanentSpec,
    StateDimension,
)
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    LoopType,
    OutputType,
    VerificationStatus,
)
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.state.paths import is_valid_state_path
from mtg_loop_engine.verify.verifier import Verifier


@pytest.mark.parametrize(
    "path",
    [
        "mana.white",
        "mana.any_color",
        "mana.generic",
        "events.death",
        "events.sacrifice",
        "life.you",
        "life.opponent",
        "permanents.p1.zone",
        "permanents.p1.tapped",
        "permanents.p1.counters.p1p1",
        "permanents.p1.summoning_sick",
        "permanents.p1.once_per_turn_used.tap-mana",
        "pending_triggers.count",
        "count.battlefield.creature_tokens",
        "count.battlefield.creatures",
        "count.battlefield.artifacts",
    ],
)
def test_valid_state_paths_accepted(path: str):
    assert is_valid_state_path(path)
    dim = StateDimension(path=path, op=ComparisonOp.EXACT, value=0)
    assert dim.path == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "bogus.root",
        "mana.purple",
        "life.both",
        "permanents.p1.unknown_attr",
        "permanents.p1.counters",
        "pending_triggers",
        "pending_triggers.depth",
        "count.battlefield.enchantments",
        "count.bogus.creatures",
        "events",
        "mana",
    ],
)
def test_invalid_state_paths_rejected_at_construction(path: str):
    assert not is_valid_state_path(path)
    with pytest.raises(ValidationError):
        StateDimension(path=path, op=ComparisonOp.EXACT, value=0)


def test_invalid_path_in_witness_not_verified():
    """Defense in depth: bypass pydantic, verifier still typed-rejects."""
    bad = StateDimension.model_construct(
        path="bogus.root",
        op=ComparisonOp.EXACT,
        value=0,
    )
    witness = LoopWitness(
        id="bad-path",
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
        initial_state=InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="a", oracle_id="a", name="A", is_creature=True
                ),
                PermanentSpec(
                    object_id="b", oracle_id="b", name="B", is_creature=True
                ),
            ]
        ),
        loop_actions=[ActionStep(op="noop")],
        relevant_state=LoopRelevantState(dimensions=[bad]),
        expected_outputs=[
            OutputDelta(type=OutputType.OTHER, delta_per_iteration=1),
        ],
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.STATE_NOT_RECURRENT
    assert proof.status != VerificationStatus.VERIFIED
    assert proof.rejection_reason is not None
    assert "invalid state path" in proof.rejection_reason
