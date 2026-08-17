"""Minimal proof normalization (VALID → NORMALIZED)."""

from __future__ import annotations

from mtg_loop_engine.proofs.models import LoopProof
from mtg_loop_engine.semantics.enums import ProofKind


def normalize_proof(proof: LoopProof) -> LoopProof:
    """Light normalization: drop noop actions; mark kind NORMALIZED.

    Does not claim mathematical minimality.
    """
    data = proof.model_copy(deep=True)
    data.setup_actions = [a for a in data.setup_actions if a.op != "noop"]
    data.loop_actions = [a for a in data.loop_actions if a.op != "noop"]
    data.kind = ProofKind.NORMALIZED
    return data
