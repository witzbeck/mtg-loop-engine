"""Compiled IR must be executable by the M1 verifier (basalt + training)."""

from mtg_loop_engine.proofs.models import (
    ActionStep,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    OutputDelta,
    PermanentSpec,
    StateDimension,
)
from mtg_loop_engine.corpus.builders import two_card
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    Consequence,
    OutputType,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.ir import ActivatedAbility, UntapEffect
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.verify.verifier import Verifier


def _compile(oracle_id: str):
    fix = GOLD_ORACLE_FIXTURES[oracle_id]
    return compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    ).semantics


def test_compiled_basalt_training_verifies():
    basalt = _compile("oracle:basalt-monolith")
    grounds = _compile("synthetic:generic-activated-cost-reducer")
    tap_id = next(
        a.ability_id
        for a in basalt.abilities
        if isinstance(a, ActivatedAbility) and a.is_mana_ability
    )
    untap_id = next(
        a.ability_id
        for a in basalt.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, UntapEffect) for e in a.effects)
    )
    witness = LoopWitness(
        id="compiled_basalt_training",
        classification=two_card(
            essential=[
                EssentialCardRef(oracle_id=basalt.oracle_id, name=basalt.name),
                EssentialCardRef(oracle_id=grounds.oracle_id, name=grounds.name),
            ]
        ),
        essential_cards=[
            EssentialCardRef(oracle_id=basalt.oracle_id, name=basalt.name),
            EssentialCardRef(oracle_id=grounds.oracle_id, name=grounds.name),
        ],
        card_semantics=[basalt, grounds],
        initial_state=InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_basalt",
                    oracle_id=basalt.oracle_id,
                    name=basalt.name,
                    zone=Zone.BATTLEFIELD,
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="p_tg",
                    oracle_id=grounds.oracle_id,
                    name=grounds.name,
                    zone=Zone.BATTLEFIELD,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_basalt", ability_id=tap_id),
            ActionStep(op="activate", actor="p_basalt", ability_id=untap_id),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(
                    path="permanents.p_basalt.zone",
                    op=ComparisonOp.EXACT,
                    value="battlefield",
                ),
                StateDimension(
                    path="permanents.p_basalt.tapped",
                    op=ComparisonOp.EXACT,
                    value=False,
                ),
                StateDimension(
                    path="mana.colorless", op=ComparisonOp.MINIMUM, value=0
                ),
            ]
        ),
        expected_outputs=[
            OutputDelta(type=OutputType.MANA, delta_per_iteration=3),
            OutputDelta(type=OutputType.UNTAP, delta_per_iteration=1),
        ],
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED, (
        f"{proof.status} {proof.rejection_reason} {proof.recurrence}"
    )
