"""Classify verified discoveries against a Spellbook-style name-pair reference."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from mtg_loop_engine.config import EngineConfig
from mtg_loop_engine.eval.explain import record_from_hit
from mtg_loop_engine.eval.schema import CandidateRecord, ReferenceStatus
from mtg_loop_engine.eval.store import AdjudicationStore
from mtg_loop_engine.search.discover import DiscoveryHit, DiscoveryReport

CORPUS_SPELLBOOK_ABSENT = "spellbook_absent"

# Working (gitignored) JSONL for workbench import; not a frozen baseline.
DEFAULT_ABSENT_JSONL = (
    Path(__file__).resolve().parents[3] / "data" / "eval" / "spellbook_absent.jsonl"
)


class ReferencePairHit(BaseModel):
    """One verified discovery labeled relative to the reference corpus."""

    left_name: str
    right_name: str
    left_oracle_id: str
    right_oracle_id: str
    reasons: list[str] = Field(default_factory=list)
    reference_status: ReferenceStatus
    proof_hash: str = ""


class AbsentDiscoveryReport(BaseModel):
    """Blind discovery hits partitioned by Spellbook (or other) membership."""

    pool_cards: int = 0
    candidate_pairs: int = 0
    searched_pairs: int = 0
    verified: int = 0
    in_reference: int = 0
    absent_from_reference: int = 0
    hits: list[ReferencePairHit] = Field(default_factory=list)
    notes: str = (
        "ABSENT_FROM_REFERENCE is a label, not a false positive. "
        "NOVEL requires human adjudication (ADR 0005)."
    )


def name_pair_key(left: str, right: str) -> frozenset[str]:
    return frozenset({left.casefold(), right.casefold()})


def reference_pair_keys(pairs: Iterable[tuple[str, str] | frozenset[str]]) -> set[frozenset[str]]:
    keys: set[frozenset[str]] = set()
    for pair in pairs:
        if isinstance(pair, frozenset):
            keys.add(frozenset(n.casefold() for n in pair))
        else:
            left, right = pair
            keys.add(name_pair_key(left, right))
    return keys


def _status_for_hit(
    hit: DiscoveryHit, keys: set[frozenset[str]]
) -> ReferenceStatus | None:
    refs = sorted(hit.witness.essential_cards, key=lambda c: c.name.casefold())
    if len(refs) != 2:
        return None
    key = name_pair_key(refs[0].name, refs[1].name)
    if key in keys:
        return ReferenceStatus.IN_REFERENCE
    return ReferenceStatus.ABSENT_FROM_REFERENCE


def classify_discovery_vs_reference(
    discovery: DiscoveryReport,
    reference_pairs: Iterable[tuple[str, str] | frozenset[str]],
) -> AbsentDiscoveryReport:
    """Label each verified hit as in-reference or ABSENT_FROM_REFERENCE.

    Pair labels are used only for scoring after search — never fed into discovery.
    """
    keys = reference_pair_keys(reference_pairs)
    hits: list[ReferencePairHit] = []
    in_ref = 0
    absent = 0
    for hit in discovery.verified:
        refs = sorted(hit.witness.essential_cards, key=lambda c: c.name.casefold())
        if len(refs) != 2:
            continue
        left, right = refs[0], refs[1]
        status = _status_for_hit(hit, keys)
        if status is None:
            continue
        if status == ReferenceStatus.IN_REFERENCE:
            in_ref += 1
        else:
            absent += 1
        hits.append(
            ReferencePairHit(
                left_name=left.name,
                right_name=right.name,
                left_oracle_id=left.oracle_id,
                right_oracle_id=right.oracle_id,
                reasons=list(hit.reasons),
                reference_status=status,
                proof_hash=hit.proof.proof_hash,
            )
        )
    hits.sort(key=lambda h: (h.reference_status.value, h.left_name, h.right_name))
    return AbsentDiscoveryReport(
        pool_cards=discovery.cards,
        candidate_pairs=discovery.candidate_pairs,
        searched_pairs=discovery.searched_pairs,
        verified=len(hits),
        in_reference=in_ref,
        absent_from_reference=absent,
        hits=hits,
    )


def candidate_records_from_discovery(
    discovery: DiscoveryReport,
    reference_pairs: Iterable[tuple[str, str] | frozenset[str]],
    *,
    corpus: str = CORPUS_SPELLBOOK_ABSENT,
    only_absent: bool = True,
    oracle_text: dict[str, str] | None = None,
    engine_version: str | None = None,
) -> list[CandidateRecord]:
    """Build workbench candidates from verified discovery hits.

    Default: only `ABSENT_FROM_REFERENCE` rows for corpus `spellbook_absent`.
    Never auto-sets `NOVEL`.
    """
    keys = reference_pair_keys(reference_pairs)
    version = engine_version or EngineConfig().engine_version
    records: list[CandidateRecord] = []
    for hit in discovery.verified:
        status = _status_for_hit(hit, keys)
        if status is None:
            continue
        if only_absent and status != ReferenceStatus.ABSENT_FROM_REFERENCE:
            continue
        records.append(
            record_from_hit(
                witness=hit.witness,
                proof=hit.proof,
                reasons=hit.reasons,
                corpus=corpus,
                reference_status=status,
                engine_version=version,
                oracle_text=oracle_text,
            )
        )
    records.sort(key=lambda r: (r.left_name, r.right_name))
    return records


def persist_spellbook_absent_candidates(
    records: list[CandidateRecord],
    store: AdjudicationStore,
    *,
    jsonl_path: Path | None = None,
) -> list[CandidateRecord]:
    """Upsert absent candidates into the workbench store and export corpus JSONL."""
    out = jsonl_path or DEFAULT_ABSENT_JSONL
    for record in records:
        if record.corpus != CORPUS_SPELLBOOK_ABSENT:
            raise ValueError(
                f"expected corpus={CORPUS_SPELLBOOK_ABSENT!r}, got {record.corpus!r}"
            )
        if record.reference_status == ReferenceStatus.NOVEL:
            raise ValueError("persist must not write NOVEL without human adjudication")
        store.upsert_candidate(record)
    store.export_jsonl(out, corpus=CORPUS_SPELLBOOK_ABSENT)
    return records


def hit_names(hit: DiscoveryHit) -> tuple[str, str]:
    refs = sorted(hit.witness.essential_cards, key=lambda c: c.name.casefold())
    return refs[0].name, refs[1].name
