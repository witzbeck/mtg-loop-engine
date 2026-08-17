"""Blind discovery orchestration: cards → pairs → search → verifier."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.proofs.models import LoopProof, LoopWitness
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.verify.verifier import Verifier


class DiscoveryHit(BaseModel):
    witness: LoopWitness
    proof: LoopProof
    reasons: list[str] = Field(default_factory=list)


class DiscoveryReport(BaseModel):
    cards: int
    candidate_pairs: int
    searched_pairs: int
    verified: list[DiscoveryHit] = Field(default_factory=list)

    @property
    def verified_pairs(self) -> set[frozenset[str]]:
        return {
            frozenset(c.oracle_id for c in hit.witness.essential_cards)
            for hit in self.verified
        }


def discover_loops(
    cards: list[CardSemantics],
    *,
    max_depth: int = 6,
    verifier: Verifier | None = None,
) -> DiscoveryReport:
    """Find two-card loops without known pairing information.

    Pair labels must not be passed in. The injected verifier is the same
    conservative witness-in engine used for gold_core, and it is the search
    acceptance oracle (one verify per candidate sequence; no second pass).
    """
    check = verifier or Verifier()
    index = InteractionIndex(cards)
    pairs = index.candidate_pairs()
    report = DiscoveryReport(
        cards=len(index.cards),
        candidate_pairs=len(pairs),
        searched_pairs=0,
    )
    for pair in pairs:
        left = index.cards[pair.left_id]
        right = index.cards[pair.right_id]
        report.searched_pairs += 1
        found = explore_pair(left, right, max_depth=max_depth, verifier=check)
        if found is None:
            continue
        report.verified.append(
            DiscoveryHit(
                witness=found.witness,
                proof=found.proof,
                reasons=pair.reasons,
            )
        )
    return report
