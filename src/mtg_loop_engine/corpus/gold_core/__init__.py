"""Gold-core: Oracle-exact positives and counterfactuals only (ADR 0007)."""

from mtg_loop_engine.corpus.gold_core.hard_negatives import hard_negatives
from mtg_loop_engine.corpus.gold_core.oracle_cases import all_gold_core

__all__ = ["all_gold_core", "hard_negatives"]
