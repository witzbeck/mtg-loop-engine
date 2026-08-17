"""Blind discovery orchestration: cards → pairs → search → verifier."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.proofs.models import LoopProof, LoopWitness
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.enums import VerificationStatus
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

    Pair labels must not be passed in. The verifier is the same conservative
    witness-in engine used for gold_core.
    """
    _ = verifier  # reserved; explorer already uses Verifier()
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
        witness = explore_pair(left, right, max_depth=max_depth)
        if witness is None:
            continue
        proof = Verifier().verify(witness)
        if proof.status == VerificationStatus.VERIFIED:
            report.verified.append(
                DiscoveryHit(witness=witness, proof=proof, reasons=pair.reasons)
            )
    return report
