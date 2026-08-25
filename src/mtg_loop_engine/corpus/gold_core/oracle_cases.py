"""Oracle-exact gold_core positives (ADR 0007).

Wave 0: empty. Waves 1–3 promote real ORACLE_EXACT×ORACLE_EXACT witnesses here
with new IDs (never reuse historical physics `core_*` claim IDs).
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import LoopWitness


def all_gold_core() -> list[LoopWitness]:
    """Return Oracle-exact gold positives only (empty until Wave 1 promotions)."""
    return []


__all__ = ["all_gold_core"]
