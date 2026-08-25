"""Corpus package exports."""

from mtg_loop_engine.corpus.gold_core.cases import (
    all_gold_core,
    gold_extended_catalog,
    hard_negatives,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import Provenance
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def gold_core_card_pool() -> list[CardSemantics]:
    """Unique gold_core cards with pair labels stripped (mixed provenance)."""
    seen: dict[str, CardSemantics] = {}
    for witness in all_gold_core():
        for card in witness.card_semantics:
            seen.setdefault(card.oracle_id, card)
    return list(seen.values())


def physics_gold_card_pool() -> list[CardSemantics]:
    """Gold-core cards allowed for engine-physics evaluation (SYNTHETIC ok).

    Includes temporary ORACLE_DIVERGENT quarantine entries until migrated.
    """
    return gold_core_card_pool()


def oracle_gold_card_pool() -> list[CardSemantics]:
    """Gold-core cards with ORACLE_EXACT provenance only."""
    out: list[CardSemantics] = []
    for card in gold_core_card_pool():
        fixture = GOLD_ORACLE_FIXTURES.get(card.oracle_id)
        if fixture is not None and fixture.provenance is Provenance.ORACLE_EXACT:
            out.append(card)
    return out


def gold_core_pair_keys() -> set[frozenset[str]]:
    return {
        frozenset(card.oracle_id for card in witness.essential_cards)
        for witness in all_gold_core()
    }


def _compile_fixture(oracle_id: str) -> CardSemantics:
    fixture = GOLD_ORACLE_FIXTURES[oracle_id]
    report = compile_oracle_text(
        oracle_id=fixture.oracle_id,
        name=fixture.name,
        oracle_text=fixture.oracle_text,
        types=fixture.types,
    )
    return report.semantics


def gold_core_compiled_card_pool() -> list[CardSemantics]:
    """Compile gold fixtures for gold_core ids. Pair labels stay hidden."""
    return [_compile_fixture(card.oracle_id) for card in gold_core_card_pool()]


def physics_gold_compiled_card_pool() -> list[CardSemantics]:
    """Compiled physics pool (SYNTHETIC / divergent allowed)."""
    return gold_core_compiled_card_pool()


def oracle_gold_compiled_card_pool() -> list[CardSemantics]:
    """Compiled ORACLE_EXACT gold-core cards only."""
    return [_compile_fixture(card.oracle_id) for card in oracle_gold_card_pool()]


__all__ = [
    "all_gold_core",
    "gold_core_card_pool",
    "gold_core_compiled_card_pool",
    "gold_core_pair_keys",
    "gold_extended_catalog",
    "hard_negatives",
    "oracle_gold_card_pool",
    "oracle_gold_compiled_card_pool",
    "physics_gold_card_pool",
    "physics_gold_compiled_card_pool",
]
