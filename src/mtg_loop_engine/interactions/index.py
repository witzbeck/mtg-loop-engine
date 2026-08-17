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

    def _complement_ids(self, oid: str) -> set[str]:
        """Inverted-index neighborhood that might join with oid."""
        cap = self.caps[oid]
        out: set[str] = set()
        if cap.produces & {"etb", "token"}:
            out |= self.by_triggers["enter_battlefield"]
        if "enter_battlefield" in cap.triggers_on:
            out |= self.by_produces["etb"] | self.by_produces["token"]
        if "tap" in cap.requires:
            out |= self.by_produces["untap"]
        if "untap" in cap.produces:
            out |= self.by_requires["tap"]
        if cap.requires & {"sac_creature", "sac_self", "sac_token"}:
            out |= (
                self.by_produces["gy_return"]
                | self.by_produces["dies_return"]
                | self.by_triggers["dies"]
            )
        if cap.produces & {"gy_return", "dies_return"} or "dies" in cap.triggers_on:
            out |= (
                self.by_requires["sac_creature"]
                | self.by_requires["sac_self"]
                | self.by_requires["sac_token"]
            )
        if "remove_counter" in cap.requires:
            out |= self.by_produces["add_counter"]
        if "add_counter" in cap.produces:
            out |= self.by_requires["remove_counter"]
        if "mana" in cap.requires:
            out |= self.by_modifies["reduce_activation_cost"] | self.by_produces["mana"]
        if "reduce_activation_cost" in cap.modifies:
            out |= self.by_requires["mana"]
        if "mana" in cap.produces:
            out |= self.by_requires["mana"]
        out.discard(oid)
        return out

    def candidate_pairs(self) -> list[CandidatePair]:
        """Unordered complementary pairs. Does not consult known combo labels."""
        seen: set[tuple[str, str]] = set()
        pairs: list[CandidatePair] = []
        for left_id in sorted(self.cards):
            for right_id in sorted(self._complement_ids(left_id)):
                key = tuple(sorted((left_id, right_id)))
                if key in seen:
                    continue
                seen.add(key)
                reasons = join_reasons(self.caps[key[0]], self.caps[key[1]])
                reasons += join_reasons(self.caps[key[1]], self.caps[key[0]])
                uniq: list[str] = []
                for reason in reasons:
                    if reason not in uniq:
                        uniq.append(reason)
                if not uniq:
                    continue
                pairs.append(
                    CandidatePair(left_id=key[0], right_id=key[1], reasons=uniq)
                )
        return pairs
