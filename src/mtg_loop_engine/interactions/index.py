"""Inverted capability index and complementary pair generation."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from mtg_loop_engine.interactions.capabilities import (
    CardCapabilities,
    extract_capabilities,
    join_reasons,
)
from mtg_loop_engine.semantics.ir import CardSemantics


class CandidatePair(BaseModel):
    left_id: str
    right_id: str
    reasons: list[str] = Field(default_factory=list)


class InteractionIndex:
    def __init__(self, cards: list[CardSemantics]):
        self.cards = {c.oracle_id: c for c in cards if not c.relevant_unsupported()}
        self.caps: dict[str, CardCapabilities] = {
            oid: extract_capabilities(card) for oid, card in self.cards.items()
        }
        self.by_produces: dict[str, set[str]] = defaultdict(set)
        self.by_requires: dict[str, set[str]] = defaultdict(set)
        self.by_triggers: dict[str, set[str]] = defaultdict(set)
        self.by_modifies: dict[str, set[str]] = defaultdict(set)
        for oid, cap in self.caps.items():
            for tag in cap.produces:
                self.by_produces[tag].add(oid)
            for tag in cap.requires:
                self.by_requires[tag].add(oid)
            for tag in cap.triggers_on:
                self.by_triggers[tag].add(oid)
            for tag in cap.modifies:
                self.by_modifies[tag].add(oid)

    def candidate_pairs(self) -> list[CandidatePair]:
        """Unordered complementary pairs. Does not consult known combo labels."""
        seen: set[tuple[str, str]] = set()
        pairs: list[CandidatePair] = []
        ids = sorted(self.cards)
        for i, left_id in enumerate(ids):
            for right_id in ids[i + 1 :]:
                reasons = join_reasons(self.caps[left_id], self.caps[right_id])
                reasons += join_reasons(self.caps[right_id], self.caps[left_id])
                # Unique while preserving order
                uniq: list[str] = []
                for r in reasons:
                    if r not in uniq:
                        uniq.append(r)
                if not uniq:
                    continue
                key = (left_id, right_id)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(
                    CandidatePair(left_id=left_id, right_id=right_id, reasons=uniq)
                )
        return pairs
