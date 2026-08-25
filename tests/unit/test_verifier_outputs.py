"""Verifier rejects non-productive loops (empty / insufficient outputs)."""

from mtg_loop_engine.corpus.builders import bf, dim, out, two_card, witness
from mtg_loop_engine.corpus.gold_core.cases import BASALT, SYNTHETIC_COST_REDUCER
from mtg_loop_engine.proofs.models import (
    ActionStep,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
)
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    OutputType,
    VerificationStatus,
)
from mtg_loop_engine.verify.verifier import Verifier


def _refs(*cards):
    return [EssentialCardRef(oracle_id=c.oracle_id, name=c.name) for c in cards]


def _basalt_grounds_actions():
    return [
        ActionStep(op="activate", actor="p_basalt", ability_id="basalt-tap-mana"),
        ActionStep(op="activate", actor="p_basalt", ability_id="basalt-untap"),
    ]


def _basalt_grounds_board():
    return [
        bf("p_basalt", BASALT.oracle_id, BASALT.name, is_artifact=True),
        bf("p_grounds", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
    ]


def test_empty_expected_outputs_is_not_a_loop():
    """Physics may recur; without declared productive outputs → NOT_A_LOOP."""
    w = witness(
        id="neg_empty_outputs",
        classification=two_card(essential=_refs(BASALT, SYNTHETIC_COST_REDUCER)),
        essential_cards=_refs(BASALT, SYNTHETIC_COST_REDUCER),
        card_semantics=[BASALT, SYNTHETIC_COST_REDUCER],
        initial_state=InitialStateSpec(permanents=_basalt_grounds_board()),
        loop_actions=_basalt_grounds_actions(),
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_basalt.tapped", ComparisonOp.EXACT, False),
                dim("mana.colorless", ComparisonOp.MINIMUM, 0),
            ]
        ),
        expected_outputs=[],
        expected_status=VerificationStatus.NOT_A_LOOP,
        tier="hard_negative",
    )
    proof = Verifier().verify(w)
    assert proof.status == VerificationStatus.NOT_A_LOOP
    assert proof.rejection_reason is not None
    assert "no expected outputs" in proof.rejection_reason


def test_insufficient_output_delta_is_not_a_loop():
    w = witness(
        id="neg_insufficient_mana_delta",
        classification=two_card(essential=_refs(BASALT, SYNTHETIC_COST_REDUCER)),
        essential_cards=_refs(BASALT, SYNTHETIC_COST_REDUCER),
        card_semantics=[BASALT, SYNTHETIC_COST_REDUCER],
        initial_state=InitialStateSpec(permanents=_basalt_grounds_board()),
        loop_actions=_basalt_grounds_actions(),
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_basalt.tapped", ComparisonOp.EXACT, False),
                dim("mana.colorless", ComparisonOp.MINIMUM, 0),
            ]
        ),
        # Real loop produces mana event +3; claim +99 → insufficient.
        expected_outputs=[out(OutputType.MANA, 99)],
        expected_status=VerificationStatus.NOT_A_LOOP,
        tier="hard_negative",
    )
    proof = Verifier().verify(w)
    assert proof.status == VerificationStatus.NOT_A_LOOP
    assert proof.rejection_reason is not None
    assert "mana" in proof.rejection_reason
