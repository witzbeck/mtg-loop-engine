"""Snapshot gold-pool extras (accepted pairs beyond gold_core labels)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from mtg_loop_engine.config import EngineConfig
from mtg_loop_engine.corpus import gold_core_card_pool, gold_core_pair_keys
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
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES

DEFAULT_SUMMARY = Path(__file__).resolve().parents[3] / "eval" / "baseline" / "m4_gold_pool_summary.json"

# Oracle IDs of gold-corpus test fixtures that have no real Magic card equivalent.
# Any extra discovery involving one of these IDs is INVALID_CANDIDATE_DATA and is
# excluded from precision metrics.
FIXTURE_ORACLE_IDS: frozenset[str] = frozenset(
    oid for oid, fx in GOLD_ORACLE_FIXTURES.items() if fx.is_fixture
)


def _pair_has_fixture(left_id: str, right_id: str) -> bool:
    return bool({left_id, right_id} & FIXTURE_ORACLE_IDS)


# Human adjudication of extras still accepted after the participant gate
# (search requires strict_two_card). Keys are frozensets of oracle ids.
# Notes explain the class; they are not search hints.
# Pairs containing fictional fixture cards are INVALID_CANDIDATE_DATA.
#
# Pre-gate bystander duplicates (Basalt self-untap + spectator) are no longer
# discovered; they are regression-locked in tests/eval/test_classify_store.py.
# Frozen baselines under eval/baseline/ match this post-gate adjudication set
# (ROADMAP M4 items 5–6).
GOLD_EXTRA_ADJUDICATIONS: dict[frozenset[str], tuple[AdjudicationClass, str]] = {
    # ---- Real-card pairs (precision-eligible) --------------------------------
    frozenset({"oracle:ashnods-altar", "oracle:phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifices Persistent Phoenix; dies-return closes. Both pieces required.",
    ),
    frozenset({"oracle:phoenix", "oracle:phyrexian-altar"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Phyrexian Altar sacrifices Persistent Phoenix; dies-return closes.",
    ),
    frozenset({"oracle:phyrexian-altar", "oracle:reassembling-skeleton"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifice plus Skeleton's graveyard return. Distinct from Ashnod gold pair.",
    ),
    # ---- Fixture pairs (excluded from precision) -----------------------------
    frozenset({"oracle:ashnods-altar", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (oracle:suicidal-phoenix) is a gold-core fixture with no real Oracle card.",
    ),
    frozenset({"oracle:etb-ping", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Both cards are gold-core fixtures (Impact Tremors Lite, Ember Phoenix); no real Oracle cards.",
    ),
    frozenset({"oracle:phyrexian-altar", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (oracle:suicidal-phoenix) is a gold-core fixture with no real Oracle card.",
    ),
    frozenset({"oracle:soul-warden", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (oracle:suicidal-phoenix) is a gold-core fixture with no real Oracle card.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:self-untap-tapper"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Perpetual Apprentice (oracle:self-untap-tapper) is a gold-core fixture with no real Oracle card.",
    ),
    frozenset({"oracle:intruder-alarm", "oracle:self-untap-tapper"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Perpetual Apprentice (oracle:self-untap-tapper) is a gold-core fixture with no real Oracle card.",
    ),
    frozenset({"oracle:intruder-alarm", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.INVALID_CANDIDATE_DATA,
        "Ember Phoenix (oracle:suicidal-phoenix) is a gold-core fixture with no real Oracle card.",
    ),
}


def collect_gold_pool_extras(*, max_depth: int = 6) -> list[CandidateRecord]:
    """Run unlabeled discovery on gold_core cards and keep non-gold accepted pairs.

    Pairs where either card is a fixture stand-in (is_fixture=True) are still
    returned but will be auto-labelled INVALID_CANDIDATE_DATA by
    persist_gold_pool_extras. They are excluded from precision metrics.
    """
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
                raise RuntimeError(f"no adjudication for {record.left_name} + {record.right_name}")
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
    store.export_jsonl(jsonl_path)
    adjs = {
        record.candidate_id: store.get_adjudication(record.candidate_id)
        for record in extras
    }
    # Separate precision-eligible (real-card) pairs from fixture pairs
    real_extras = [
        r for r in extras if not _pair_has_fixture(r.left_id, r.right_id)
    ]
    fixture_count = len(extras) - len(real_extras)
    report = precision_from_records(real_extras, {k: v for k, v in adjs.items() if v})
    summary = {
        "extras_total": len(extras),
        "extras_real_card_pairs": len(real_extras),
        "extras_fixture_pairs": fixture_count,
        "adjudicated": report.adjudicated,
        "valid": report.valid,
        "precision": report.precision,
        "by_class": report.by_class,
        "notes": (
            "Precision computed over real-card pairs only; fixture pairs "
            "(is_fixture=True) are INVALID_CANDIDATE_DATA and excluded. "
            "Joins were not tightened to chase this distribution."
        ),
    }
    out = summary_path or DEFAULT_SUMMARY
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return extras
