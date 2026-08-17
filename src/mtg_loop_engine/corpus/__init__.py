"""Corpus package exports."""

from mtg_loop_engine.corpus.gold_core.cases import (
    all_gold_core,
    gold_extended_catalog,
    hard_negatives,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


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


def gold_core_compiled_card_pool() -> list[CardSemantics]:
    """Compile gold Oracle fixtures for gold_core ids. Pair labels stay hidden."""
    pool: list[CardSemantics] = []
    for card in gold_core_card_pool():
        fixture = GOLD_ORACLE_FIXTURES[card.oracle_id]
        report = compile_oracle_text(
            oracle_id=fixture.oracle_id,
            name=fixture.name,
            oracle_text=fixture.oracle_text,
            types=fixture.types,
        )
        pool.append(report.semantics)
    return pool


__all__ = [
    "all_gold_core",
    "gold_core_card_pool",
    "gold_core_compiled_card_pool",
    "gold_core_pair_keys",
    "gold_extended_catalog",
    "hard_negatives",
]
