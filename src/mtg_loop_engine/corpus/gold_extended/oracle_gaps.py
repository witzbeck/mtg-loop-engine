"""Real Oracle pairs blocked by unsupported semantics (promotion staging).

Park Wave 2/3 candidates here until primitives exist. Not precision-eligible.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import LoopWitness


def oracle_gap_catalog() -> list[LoopWitness]:
    """Stub catalog for real pairs awaiting executor/compiler support."""
    return []


__all__ = ["oracle_gap_catalog"]
