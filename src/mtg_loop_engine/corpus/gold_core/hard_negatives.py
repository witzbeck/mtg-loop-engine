"""Oracle-exact hard negatives for gold_core.

Wave 0: empty. Counterfactuals for promoted Oracle pairs land here in Waves 1–3.
Physics-tied negatives live under ``corpus.physics_fixtures``.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import LoopWitness


def hard_negatives() -> list[LoopWitness]:
    """Oracle-exact counterfactuals paired with gold_core positives."""
    return []


__all__ = ["hard_negatives"]
