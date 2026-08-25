"""Classify verified discoveries against a Spellbook-style name-pair reference."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, Field

from mtg_loop_engine.eval.schema import ReferenceStatus
from mtg_loop_engine.search.discover import DiscoveryHit, DiscoveryReport


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
        key = name_pair_key(left.name, right.name)
        if key in keys:
            status = ReferenceStatus.IN_REFERENCE
            in_ref += 1
        else:
            status = ReferenceStatus.ABSENT_FROM_REFERENCE
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


def hit_names(hit: DiscoveryHit) -> tuple[str, str]:
    refs = sorted(hit.witness.essential_cards, key=lambda c: c.name.casefold())
    return refs[0].name, refs[1].name
