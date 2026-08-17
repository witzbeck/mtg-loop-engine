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

DEFAULT_SUMMARY = Path(__file__).resolve().parents[3] / "eval" / "baseline" / "m4_gold_pool_summary.json"

# Human adjudication of the 24 extra accepted pairs from the unlabeled gold pool.
# Keys are frozensets of oracle ids. Notes explain the class; they are not search hints.
GOLD_EXTRA_ADJUDICATIONS: dict[frozenset[str], tuple[AdjudicationClass, str]] = {
    frozenset({"oracle:ashnods-altar", "oracle:phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifices Persistent Phoenix; dies-return closes. Both pieces required.",
    ),
    frozenset({"oracle:ashnods-altar", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifices Ember Phoenix; dies-return closes. Both pieces required.",
    ),
    frozenset({"oracle:etb-ping", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Ember Phoenix self-sac/return; Tremors Lite converts ETB into damage.",
    ),
    frozenset({"oracle:phoenix", "oracle:phyrexian-altar"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Phyrexian Altar sacrifices Persistent Phoenix; dies-return closes.",
    ),
    frozenset({"oracle:phyrexian-altar", "oracle:reassembling-skeleton"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifice plus Skeleton's graveyard return. Distinct from Ashnod gold pair.",
    ),
    frozenset({"oracle:phyrexian-altar", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Altar sacrifices Ember Phoenix; dies-return closes.",
    ),
    frozenset({"oracle:soul-warden", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.VALID_STRICT_TWO_CARD,
        "Ember Phoenix loops; Soul Warden is required for the claimed life-gain output.",
    ),
    frozenset({"oracle:ashnods-altar", "oracle:basalt-monolith"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Loop body is only Basalt tap/untap. Altar is a spectator; not two essential pieces.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:gravecrawler"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Gravecrawler never acts.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:intruder-alarm"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Alarm never acts.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:phyrexian-altar"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Altar never acts.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:reassembling-skeleton"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Skeleton never acts.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:token-breeder"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Breeder unused; seeded token is also unused.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:token-tapper"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Basalt self-untap only. Eager Apprentice never acts.",
    ),
    frozenset({"oracle:basalt-monolith", "oracle:self-untap-tapper"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Loop body is only Perpetual Apprentice self-untap token. Basalt unused.",
    ),
    frozenset({"oracle:self-untap-tapper", "oracle:token-breeder"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Perpetual Apprentice solo token loop. Breeder and seed unused.",
    ),
    frozenset({"oracle:self-untap-tapper", "oracle:token-tapper"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Perpetual Apprentice solo token loop. Eager Apprentice unused.",
    ),
    frozenset({"oracle:gravecrawler", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return only. Gravecrawler unused.",
    ),
    frozenset({"oracle:phoenix", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return only. Persistent Phoenix unused.",
    ),
    frozenset({"oracle:reassembling-skeleton", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return only. Skeleton unused.",
    ),
    frozenset({"oracle:suicidal-phoenix", "oracle:token-breeder"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return only. Breeder and seed unused.",
    ),
    frozenset({"oracle:suicidal-phoenix", "oracle:viscera-seer"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return only. Seer unused (not even the sac outlet).",
    ),
    frozenset({"oracle:intruder-alarm", "oracle:self-untap-tapper"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Perpetual Apprentice already self-untaps. Alarm trigger is incidental, not required.",
    ),
    frozenset({"oracle:intruder-alarm", "oracle:suicidal-phoenix"}): (
        AdjudicationClass.DUPLICATE_OR_EQUIVALENT_INTERACTION,
        "Ember Phoenix self-sac/return. Alarm only untaps itself; not required to close the loop.",
    ),
}


def collect_gold_pool_extras(*, max_depth: int = 6) -> list[CandidateRecord]:
    """Run unlabeled discovery on gold_core cards and keep non-gold accepted pairs."""
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
    report = precision_from_records(extras, {k: v for k, v in adjs.items() if v})
    summary = {
        "extras": len(extras),
        "adjudicated": report.adjudicated,
        "valid": report.valid,
        "precision": report.precision,
        "by_class": report.by_class,
        "notes": (
            "Adjudication of unlabeled gold-pool extras. "
            "Joins were not tightened to chase this distribution. "
            "Spellbook absence is ABSENT_FROM_REFERENCE."
        ),
    }
    out = summary_path or DEFAULT_SUMMARY
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return extras
