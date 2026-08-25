"""Oracle-exact gold_core positives (ADR 0007 Wave 1+).

Witnesses are captured from blind ``explore_pair`` on audited ``ORACLE_EXACT``
fixtures, then stamped with stable gold IDs and net-state expectations.
"""

from __future__ import annotations

from mtg_loop_engine.corpus.builders import witness as rebuild_witness
from mtg_loop_engine.proofs.models import LoopWitness, NetStateDelta
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import Consequence
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.verify.verifier import Verifier


def _compile(oracle_id: str):
    fix = GOLD_ORACLE_FIXTURES[oracle_id]
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    assert report.coverage.value == "complete", (
        oracle_id,
        report.semantics.unsupported_fragments,
    )
    return report.semantics


def _promote(
    *,
    gold_id: str,
    left_id: str,
    right_id: str,
    expected_net_state: NetStateDelta,
    expected_claim_consequence: Consequence,
    max_depth: int = 8,
) -> LoopWitness:
    # Lazy import avoids corpus ↔ search circular import at package load.
    from mtg_loop_engine.search.explorer import explore_pair

    left = _compile(left_id)
    right = _compile(right_id)
    hit = explore_pair(
        left,
        right,
        max_depth=max_depth,
        expected_net_state=expected_net_state,
        expected_claim_consequence=expected_claim_consequence,
    ) or explore_pair(
        right,
        left,
        max_depth=max_depth,
        expected_net_state=expected_net_state,
        expected_claim_consequence=expected_claim_consequence,
    )
    if hit is None:
        raise RuntimeError(f"failed to rediscover {gold_id} for gold promotion")
    proof = Verifier().verify(
        hit.witness.model_copy(
            update={
                "id": gold_id,
                "expected_net_state": expected_net_state,
                "expected_claim_consequence": expected_claim_consequence,
            }
        )
    )
    if proof.status.value != "verified":
        raise RuntimeError(
            f"{gold_id} failed net-gated verify: {proof.status} {proof.rejection_reason}"
        )
    w = hit.witness
    return rebuild_witness(
        id=gold_id,
        classification=w.classification,
        essential_cards=w.essential_cards,
        card_semantics=w.card_semantics,
        initial_state=w.initial_state,
        setup_actions=w.setup_actions,
        loop_actions=w.loop_actions,
        relevant_state=w.relevant_state,
        expected_outputs=w.expected_outputs,
        expected_net_state=expected_net_state,
        expected_claim_consequence=expected_claim_consequence,
        prerequisites=w.prerequisites,
        assumptions=[a for a in w.assumptions if a != "discovered_without_pair_labels"]
        + ["oracle_exact_gold", "compiled_from_audited_fixture"],
    )


def all_gold_core() -> list[LoopWitness]:
    """Return Oracle-exact gold positives (Waves 1+)."""
    cases = [
        _promote(
            gold_id="core_guard_gond",
            left_id="oracle:midnight-guard",
            right_id="oracle:presence-of-gond",
            expected_net_state=NetStateDelta(creature_tokens=1),
            expected_claim_consequence=Consequence.ACCUMULATES,
        ),
        _promote(
            gold_id="core_altar_gravecrawler_live",
            left_id="oracle:phyrexian-altar",
            right_id="oracle:gravecrawler",
            expected_net_state=NetStateDelta(),
            expected_claim_consequence=Consequence.REPEATABLE_EVENT,
        ),
        _promote(
            gold_id="core_alarm_doomsayer",
            left_id="oracle:intruder-alarm",
            right_id="oracle:thraben-doomsayer",
            expected_net_state=NetStateDelta(creature_tokens=1),
            expected_claim_consequence=Consequence.ACCUMULATES,
        ),
        _promote(
            gold_id="core_bond_blood",
            left_id="oracle:sanguine-bond",
            right_id="oracle:exquisite-blood",
            expected_net_state=NetStateDelta(life_you=1, life_opponent=-1),
            expected_claim_consequence=Consequence.LETHAL,
        ),
        _promote(
            gold_id="core_basalt_zirda",
            left_id="oracle:basalt-monolith",
            right_id="oracle:zirda-the-dawnwaker",
            expected_net_state=NetStateDelta(mana=ManaAmount(colorless=2)),
            expected_claim_consequence=Consequence.ACCUMULATES,
        ),
        _promote(
            gold_id="core_druid_vizier",
            left_id="oracle:devoted-druid",
            right_id="oracle:vizier-of-remedies",
            expected_net_state=NetStateDelta(mana=ManaAmount(green=1)),
            expected_claim_consequence=Consequence.ACCUMULATES,
        ),
        _promote(
            gold_id="core_rosie_scurry",
            left_id="oracle:rosie-cotton-of-south-lane",
            right_id="oracle:scurry-oak",
            expected_net_state=NetStateDelta(
                creature_tokens=1,
                plus_one_counters=1,
            ),
            expected_claim_consequence=Consequence.ACCUMULATES,
            max_depth=10,
        ),
    ]
    return cases


__all__ = ["all_gold_core"]
