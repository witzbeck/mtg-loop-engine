"""Real Oracle pairs blocked by unsupported semantics (promotion staging).

Park Wave 3 candidates here until primitives exist. Not precision-eligible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OracleGap:
    """Documented blocker for a Spellbook-backed pair awaiting physics."""

    proposed_gold_id: str
    left_name: str
    right_name: str
    blockers: tuple[str, ...]
    notes: str = ""


def oracle_gap_catalog() -> list[OracleGap]:
    """Wave 3 pairs that remain fail-closed (do not simplify Oracle to force COMPLETE)."""
    return [
        OracleGap(
            proposed_gold_id="core_saffi_champion",
            left_name="Saffi Eriksdotter",
            right_name="Crypt Champion",
            blockers=(
                "delayed triggered ability from sacrifice (when target dies this turn)",
                "Crypt Champion multi-player ETB return from GY + R-spent sac clause",
                "multi-ETB ordering across delayed return",
            ),
            notes="Needs delayed-trigger stack and GY→BF ETB sequencing before promotion.",
        ),
        OracleGap(
            proposed_gold_id="core_mikaeus_triskelion",
            left_name="Mikaeus, the Unhallowed",
            right_name="Triskelion",
            blockers=(
                "undying as a granted keyword with counter-gated return",
                "static P/T anthem (+1/+1 to other non-Humans)",
                "state-based actions for lethal damage / 0 toughness",
                "damage to self as a legal 'any target' choice for undying loops",
            ),
            notes=(
                "Heliod/Ballista covers remove-counter damage + lifelink; "
                "undying/SBA layer is the remaining gap."
            ),
        ),
    ]


__all__ = ["OracleGap", "oracle_gap_catalog"]
