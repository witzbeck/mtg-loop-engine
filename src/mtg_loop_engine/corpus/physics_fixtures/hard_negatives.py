"""Physics-tied hard negatives (synthetic / divergent fixtures)."""

from mtg_loop_engine.corpus.physics_fixtures.synthetic_cases import physics_hard_negatives
from mtg_loop_engine.proofs.models import LoopWitness


def all_physics_hard_negatives() -> list[LoopWitness]:
    return physics_hard_negatives()


__all__ = ["all_physics_hard_negatives", "physics_hard_negatives"]
