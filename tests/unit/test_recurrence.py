"""Unit tests for recurrence projection."""

from mtg_loop_engine.proofs.models import (
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    Classification,
    EssentialCardRef,
    ActionStep,
    StateDimension,
)
from mtg_loop_engine.semantics.enums import ComparisonOp, LoopType, VerificationStatus
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import check_recurrence


def test_minimum_mana_recurrence():
    before = GameState.from_spec(InitialStateSpec(mana=ManaAmount(colorless=0)))
    after = GameState.from_spec(InitialStateSpec(mana=ManaAmount(colorless=1)))
    witness = LoopWitness(
        id="t",
        classification=Classification(
            essential_card_count=2, strict_two_card=True, loop_type=LoopType.ARBITRARY_REPEATABLE
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
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(path="mana.colorless", op=ComparisonOp.MINIMUM, value=0)
            ]
        ),
    )
    result = check_recurrence(before, after, witness)
    assert result.ok
