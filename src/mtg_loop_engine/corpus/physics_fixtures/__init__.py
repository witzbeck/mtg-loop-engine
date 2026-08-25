"""Physics fixtures: synthetic and divergent executor regressions (ADR 0007)."""

from mtg_loop_engine.corpus.physics_fixtures.hard_negatives import (
    all_physics_hard_negatives,
    physics_hard_negatives,
)
from mtg_loop_engine.corpus.physics_fixtures.synthetic_cases import (
    gold_extended_catalog,
    physics_all_positives,
)
from mtg_loop_engine.proofs.models import LoopWitness
from mtg_loop_engine.semantics.ir import CardSemantics


def physics_gold_card_pool() -> list[CardSemantics]:
    """Unique cards from physics positives (SYNTHETIC / divergent allowed)."""
    seen: dict[str, CardSemantics] = {}
    for witness in physics_all_positives():
        for card in witness.card_semantics:
            seen.setdefault(card.oracle_id, card)
    return list(seen.values())


def physics_gold_pair_keys() -> set[frozenset[str]]:
    return {
        frozenset(card.oracle_id for card in witness.essential_cards)
        for witness in physics_all_positives()
    }


__all__ = [
    "all_physics_hard_negatives",
    "gold_extended_catalog",
    "physics_all_positives",
    "physics_gold_card_pool",
    "physics_gold_pair_keys",
    "physics_hard_negatives",
]
