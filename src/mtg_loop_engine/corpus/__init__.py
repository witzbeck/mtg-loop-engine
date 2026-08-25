"""Corpus package exports."""

from mtg_loop_engine.corpus.gold_core.hard_negatives import hard_negatives
from mtg_loop_engine.corpus.gold_core.oracle_cases import all_gold_core
from mtg_loop_engine.corpus.gold_extended.oracle_gaps import oracle_gap_catalog
from mtg_loop_engine.corpus.physics_fixtures import (
    gold_extended_catalog,
    physics_all_positives,
    physics_gold_card_pool as _physics_pool_impl,
    physics_gold_pair_keys,
    physics_hard_negatives,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import Provenance
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def gold_core_card_pool() -> list[CardSemantics]:
    """Unique cards from Oracle gold_core positives (ORACLE_EXACT only)."""
    seen: dict[str, CardSemantics] = {}
    for witness in all_gold_core():
        for card in witness.card_semantics:
            seen.setdefault(card.oracle_id, card)
    return list(seen.values())


def physics_gold_card_pool() -> list[CardSemantics]:
    """Physics suite cards (SYNTHETIC / divergent allowed)."""
    return _physics_pool_impl()


def oracle_gold_card_pool() -> list[CardSemantics]:
    """Alias of gold_core_card_pool — Oracle positives are ORACLE_EXACT only."""
    return gold_core_card_pool()


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
    """Compile fixtures for Oracle gold_core card ids."""
    return [_compile_fixture(card.oracle_id) for card in gold_core_card_pool()]


def physics_gold_compiled_card_pool() -> list[CardSemantics]:
    """Compiled physics pool (SYNTHETIC / divergent allowed)."""
    out: list[CardSemantics] = []
    for card in physics_gold_card_pool():
        if card.oracle_id in GOLD_ORACLE_FIXTURES:
            out.append(_compile_fixture(card.oracle_id))
        else:
            out.append(card)
    return out


def oracle_gold_compiled_card_pool() -> list[CardSemantics]:
    """Compiled ORACLE_EXACT gold-core cards only."""
    return gold_core_compiled_card_pool()


__all__ = [
    "all_gold_core",
    "gold_core_card_pool",
    "gold_core_compiled_card_pool",
    "gold_core_pair_keys",
    "gold_extended_catalog",
    "hard_negatives",
    "oracle_gap_catalog",
    "oracle_gold_card_pool",
    "oracle_gold_compiled_card_pool",
    "physics_all_positives",
    "physics_gold_card_pool",
    "physics_gold_compiled_card_pool",
    "physics_gold_pair_keys",
    "physics_hard_negatives",
]
