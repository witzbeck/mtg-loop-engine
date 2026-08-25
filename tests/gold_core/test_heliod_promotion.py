"""Heliod/Ballista product re-promotion + seed_grant_lifelink quarantine."""

from __future__ import annotations

from mtg_loop_engine.corpus import all_gold_core, oracle_gap_catalog
from mtg_loop_engine.corpus.builders import LoopRelevantState, bf, dim, two_card
from mtg_loop_engine.proofs.models import (
    ActionStep,
    EssentialCardRef,
    InitialStateSpec,
    LoopWitness,
)
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import ComparisonOp, VerificationStatus
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


def test_heliod_ballista_in_gold_core():
    ids = {w.id for w in all_gold_core()}
    assert "core_heliod_ballista" in ids
    assert len(ids) == 8


def test_heliod_ballista_absent_from_oracle_gaps():
    assert "core_heliod_ballista" not in {
        g.proposed_gold_id for g in oracle_gap_catalog()
    }


def test_frozen_heliod_witness_paid_activate_no_seed():
    witness = next(w for w in all_gold_core() if w.id == "core_heliod_ballista")
    assert all(s.op != "seed_grant_lifelink" for s in witness.setup_actions)
    assert any(
        s.op == "activate" and "grant-lifelink" in (s.ability_id or "")
        for s in witness.setup_actions
    )
    ballista = next(
        p for p in witness.initial_state.permanents if "ballista" in p.name.lower()
    )
    assert ballista.power == 0
    assert ballista.toughness == 0
    assert ballista.counters.get("p1p1") == 2
    assert witness.initial_state.mana.white >= 1
    assert witness.initial_state.mana.total() >= 2
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED


def test_seed_grant_lifelink_rejected_on_oracle_product_witness():
    heliod = _compile("oracle:heliod-sun-crowned")
    ballista = _compile("oracle:walking-ballista")
    refs = [
        EssentialCardRef(oracle_id=heliod.oracle_id, name=heliod.name),
        EssentialCardRef(oracle_id=ballista.oracle_id, name=ballista.name),
    ]
    ping = next(a.ability_id for a in ballista.abilities if "counter-ping" in a.ability_id)
    reload_id = next(
        a.ability_id for a in heliod.abilities if "gain-life-p1p1" in a.ability_id
    )
    witness = LoopWitness(
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
            ],
        ),
        setup_actions=[
            ActionStep(
                op="seed_grant_lifelink",
                actor="p_heliod",
                target="p_ballista",
            )
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
                ability_id=reload_id,
                target="p_ballista",
            ),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_ballista.counters.p1p1", ComparisonOp.EXACT, 2),
            ]
        ),
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.UNSUPPORTED_RULE
    assert "seed_grant_lifelink" in (proof.rejection_reason or "")


def test_explore_pair_heliod_ballista_rediscovers_without_seed():
    heliod = _compile("oracle:heliod-sun-crowned")
    ballista = _compile("oracle:walking-ballista")
    hit = explore_pair(heliod, ballista, max_depth=10) or explore_pair(
        ballista, heliod, max_depth=10
    )
    assert hit is not None
    assert hit.proof.status == VerificationStatus.VERIFIED
    assert "seed_grant_lifelink" not in {
        s.op for s in hit.witness.setup_actions
    }
    assert any(
        s.op == "activate" and "grant-lifelink" in (s.ability_id or "")
        for s in hit.witness.setup_actions
    )
