"""Heliod/Ballista demotion + seed_grant_lifelink product quarantine."""

from __future__ import annotations

from mtg_loop_engine.corpus import all_gold_core, oracle_gap_catalog
from mtg_loop_engine.corpus.builders import (
    ActionStep,
    ComparisonOp,
    InitialStateSpec,
    LoopRelevantState,
    OutputType,
    bf,
    dim,
    out,
    two_card,
    witness,
)
from mtg_loop_engine.proofs.models import EssentialCardRef
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import VerificationStatus
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


def test_heliod_ballista_absent_from_gold_core():
    assert "core_heliod_ballista" not in {w.id for w in all_gold_core()}


def test_heliod_ballista_staged_in_oracle_gaps():
    assert "core_heliod_ballista" in {
        g.proposed_gold_id for g in oracle_gap_catalog()
    }


def test_seed_grant_lifelink_rejected_on_oracle_product_witness():
    heliod = _compile("oracle:heliod-sun-crowned")
    ballista = _compile("oracle:walking-ballista")
    refs = [
        EssentialCardRef(oracle_id=heliod.oracle_id, name=heliod.name),
        EssentialCardRef(oracle_id=ballista.oracle_id, name=ballista.name),
    ]
    ping = next(a.ability_id for a in ballista.abilities if "counter-ping" in a.ability_id)
    gain = next(
        a.ability_id
        for a in heliod.abilities
        if getattr(a, "event", None) is not None and a.event.value == "gain_life"
    )
    w = witness(
        id="hand_heliod_seed_quarantine",
        classification=two_card(essential=refs),
        essential_cards=refs,
        card_semantics=[heliod, ballista],
        initial_state=InitialStateSpec(
            permanents=[
                bf("p_heliod", heliod.oracle_id, heliod.name, is_creature=True),
                bf(
                    "p_ballista",
                    ballista.oracle_id,
                    ballista.name,
                    is_creature=True,
                    is_artifact=True,
                    power=0,
                    toughness=0,
                    counters={"p1p1": 2},
                ),
            ]
        ),
        setup_actions=[
            ActionStep(
                op="seed_grant_lifelink",
                actor="p_heliod",
                target="p_ballista",
                note="quarantined product seed",
            ),
        ],
        loop_actions=[
            ActionStep(
                op="activate",
                actor="p_ballista",
                ability_id=ping,
                target="opponent",
            ),
            ActionStep(
                op="resolve_trigger",
                actor="p_heliod",
                ability_id=gain,
                target="p_ballista",
            ),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_ballista.counters.p1p1", ComparisonOp.EXACT, 2),
            ]
        ),
        expected_outputs=[out(OutputType.DAMAGE, 1), out(OutputType.LIFE_GAIN, 1)],
    )
    proof = Verifier().verify(w)
    assert proof.status == VerificationStatus.UNSUPPORTED_RULE
    assert "seed_grant_lifelink" in (proof.rejection_reason or "")


def test_explore_pair_heliod_ballista_returns_none():
    heliod = _compile("oracle:heliod-sun-crowned")
    ballista = _compile("oracle:walking-ballista")
    assert explore_pair(heliod, ballista, max_depth=10) is None
    assert explore_pair(ballista, heliod, max_depth=10) is None
