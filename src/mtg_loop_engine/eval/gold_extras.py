"""Snapshot gold-pool extras (accepted pairs beyond gold_core labels)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from mtg_loop_engine.config import EngineConfig
from mtg_loop_engine.corpus import (
    gold_core_card_pool,
    gold_core_pair_keys,
    physics_gold_card_pool,
    physics_gold_pair_keys,
)
from mtg_loop_engine.eval.explain import record_from_hit
from mtg_loop_engine.eval.metrics import precision_from_records
from mtg_loop_engine.eval.schema import (
    AdjudicationClass,
    AdjudicationRecord,
    CandidateRecord,
    ReferenceStatus,
)
from mtg_loop_engine.eval.store import DEFAULT_JSONL, AdjudicationStore
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import Provenance
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.provenance import is_precision_eligible_ids

DEFAULT_SUMMARY = Path(__file__).resolve().parents[3] / "eval" / "baseline" / "m4_gold_pool_summary.json"

# SYNTHETIC ids (physics stand-ins). Kept as FIXTURE_ORACLE_IDS for CLI/compat.
FIXTURE_ORACLE_IDS: frozenset[str] = frozenset(
    oid
    for oid, fx in GOLD_ORACLE_FIXTURES.items()
    if fx.provenance is Provenance.SYNTHETIC
)


def _pair_has_fixture(left_id: str, right_id: str) -> bool:
    """True if either side is SYNTHETIC (legacy name: fixture)."""
    return bool({left_id, right_id} & FIXTURE_ORACLE_IDS)


# Wave 1: Oracle gold_core has four pairs; extras are other Oracle discoveries
# beyond labeled gold (still precision-eligible only if EXACT×EXACT + adjudicated).
GOLD_EXTRA_ADJUDICATIONS: dict[frozenset[str], tuple[AdjudicationClass, str]] = {
    frozenset({"oracle:intruder-alarm", "oracle:presence-of-gond"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Alarm+Gond rediscovers with aura-host seed; valid Oracle loop not yet promoted to gold_core.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:devoted-druid"}): (
        AdjudicationClass.FINITE_INTERACTION_MISCLASSIFIED_AS_LOOP,
        "Druid -1/-1 untap without Vizier is finite (lethal SBAs); Basalt is net-zero mana.",
    ),
    frozenset({"oracle:devoted-druid", "oracle:presence-of-gond"}): (
        AdjudicationClass.FINITE_INTERACTION_MISCLASSIFIED_AS_LOOP,
        "Gond+Druid token loop dies to accumulating -1/-1 counters without Vizier.",
    ),
}

# Physics-suite extras (discoveries beyond labeled physics positives). Not
# product-precision. Historical Wave-0-migration adjudication set.
PHYSICS_EXTRA_ADJUDICATIONS: dict[frozenset[str], tuple[AdjudicationClass, str]] = {
    # ---- SYNTHETIC physics extras (not product-precision) --------------------
    frozenset({"oracle:ashnods-altar", "synthetic:persistent-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Persistent Phoenix is SYNTHETIC physics (dies-return); not Oracle product evidence.",
    ),
    frozenset({"synthetic:persistent-phoenix", "oracle:phyrexian-altar"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Persistent Phoenix is SYNTHETIC; Phyrexian Altar fixture remains ORACLE_DIVERGENT.",
    ),
    # ---- Divergent quarantine physics (VALID engine claim; not precision) ---
    frozenset({"oracle:phyrexian-altar", "oracle:reassembling-skeleton"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Divergent Altar+Skeleton physics; neither side ORACLE_EXACT → not precision-eligible.",
    ),
    # ---- Other SYNTHETIC pairs -----------------------------------------------
    frozenset({"oracle:ashnods-altar", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (synthetic:suicidal-phoenix) is SYNTHETIC physics.",
    ),
    frozenset({"synthetic:etb-ping", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Both cards are SYNTHETIC physics fixtures.",
    ),
    frozenset({"oracle:phyrexian-altar", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (synthetic:suicidal-phoenix) is SYNTHETIC physics.",
    ),
    frozenset({"oracle:soul-warden", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (synthetic:suicidal-phoenix) is SYNTHETIC physics.",
    ),
    frozenset({"oracle:viscera-seer", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (synthetic:suicidal-phoenix) is SYNTHETIC physics.",
    ),
    frozenset({"oracle:basalt-monolith", "synthetic:self-untap-tapper"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Perpetual Apprentice (synthetic:self-untap-tapper) is SYNTHETIC physics.",
    ),
    frozenset({"oracle:intruder-alarm", "synthetic:self-untap-tapper"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Perpetual Apprentice (synthetic:self-untap-tapper) is SYNTHETIC physics.",
    ),
    frozenset({"oracle:intruder-alarm", "synthetic:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (synthetic:suicidal-phoenix) is SYNTHETIC physics.",
    ),
}


def collect_gold_pool_extras(*, max_depth: int = 6) -> list[CandidateRecord]:
    """Run unlabeled discovery on Oracle gold_core cards; keep non-gold accepted pairs."""
    gold = gold_core_pair_keys()
    report = discover_loops(gold_core_card_pool(), max_depth=max_depth)
    extras: list[CandidateRecord] = []
    engine = EngineConfig().engine_version
    for hit in report.verified:
        key = frozenset(c.oracle_id for c in hit.witness.essential_cards)
        if key in gold:
            continue
        extras.append(
            record_from_hit(
                witness=hit.witness,
                proof=hit.proof,
                reasons=hit.reasons,
                corpus="gold_pool_extras",
                reference_status=ReferenceStatus.ABSENT_FROM_REFERENCE,
                engine_version=engine,
            )
        )
    extras.sort(key=lambda r: (r.left_name, r.right_name))
    return extras


def collect_physics_pool_extras(*, max_depth: int = 6) -> list[CandidateRecord]:
    """Discoveries beyond labeled physics positives (engine regression, not precision)."""
    labeled = physics_gold_pair_keys()
    report = discover_loops(physics_gold_card_pool(), max_depth=max_depth)
    extras: list[CandidateRecord] = []
    engine = EngineConfig().engine_version
    for hit in report.verified:
        key = frozenset(c.oracle_id for c in hit.witness.essential_cards)
        if key in labeled:
            continue
        extras.append(
            record_from_hit(
                witness=hit.witness,
                proof=hit.proof,
                reasons=hit.reasons,
                corpus="physics_pool_extras",
                reference_status=ReferenceStatus.ABSENT_FROM_REFERENCE,
                engine_version=engine,
            )
        )
    extras.sort(key=lambda r: (r.left_name, r.right_name))
    return extras


def persist_gold_pool_extras(
    store: AdjudicationStore,
    *,
    apply_adjudications: bool = True,
    jsonl_path=DEFAULT_JSONL,
    summary_path: Path | None = None,
) -> list[CandidateRecord]:
    extras = collect_gold_pool_extras()
    if len(extras) != len(GOLD_EXTRA_ADJUDICATIONS):
        raise RuntimeError(
            f"expected {len(GOLD_EXTRA_ADJUDICATIONS)} extras, found {len(extras)}"
        )
    now = datetime.now(timezone.utc)
    for record in extras:
        store.upsert_candidate(record)
        key = frozenset({record.left_id, record.right_id})
        if apply_adjudications:
            if key not in GOLD_EXTRA_ADJUDICATIONS:
                raise RuntimeError(
                    f"no adjudication for {record.left_name} + {record.right_name}"
                )
            klass, notes = GOLD_EXTRA_ADJUDICATIONS[key]
            store.save_adjudication(
                AdjudicationRecord(
                    candidate_id=record.candidate_id,
                    adjudication=klass,
                    notes=notes,
                    reviewed_at=now,
                    proof_hash=record.proof.proof_hash,
                    engine_version=record.engine_version,
                    skipped=False,
                )
            )
    store.export_jsonl(jsonl_path, corpus="gold_pool_extras")
    adjs = {
        record.candidate_id: store.get_adjudication(record.candidate_id)
        for record in extras
    }
    precision_extras = [
        r for r in extras if is_precision_eligible_ids(r.left_id, r.right_id)
    ]
    non_precision = len(extras) - len(precision_extras)
    report = precision_from_records(
        precision_extras, {k: v for k, v in adjs.items() if v}
    )
    summary = {
        "extras_total": len(extras),
        "extras_real_card_pairs": len(precision_extras),
        "extras_fixture_pairs": non_precision,
        "adjudicated": report.adjudicated,
        "valid": report.valid,
        "precision": report.precision,
        "by_class": report.by_class,
        "notes": (
            "ADR 0007: precision denominator is ORACLE_EXACT×ORACLE_EXACT only "
            "(is_precision_eligible_ids). Pre-migration gold-pool precision 1.0 "
            "is historical and not comparable. Zero eligible pairs → precision null."
        ),
    }
    out = summary_path or DEFAULT_SUMMARY
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return extras
