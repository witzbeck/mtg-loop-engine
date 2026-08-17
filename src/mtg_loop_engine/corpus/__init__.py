"""Corpus package exports."""

from mtg_loop_engine.corpus.gold_core.cases import (
    all_gold_core,
    gold_extended_catalog,
    hard_negatives,
)
from mtg_loop_engine.semantics.ir import CardSemantics


def gold_core_card_pool() -> list[CardSemantics]:
    """Unique gold_core cards with pair labels stripped."""
    seen: dict[str, CardSemantics] = {}
    for witness in all_gold_core():
        for card in witness.card_semantics:
            seen.setdefault(card.oracle_id, card)
    return list(seen.values())


def gold_core_pair_keys() -> set[frozenset[str]]:
    return {
        frozenset(card.oracle_id for card in witness.essential_cards)
        for witness in all_gold_core()
    }


__all__ = [
    "all_gold_core",
    "gold_core_card_pool",
    "gold_core_pair_keys",
    "gold_extended_catalog",
    "hard_negatives",
]
