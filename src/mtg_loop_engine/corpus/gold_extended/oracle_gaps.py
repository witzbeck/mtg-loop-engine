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
                "Mikaeus undying grant / non-Human anthem not compiled from audited Oracle",
                "static P/T anthem continuous layers (+1/+1 to other non-Humans)",
                "gold promotion blocked pending audited Oracle witness",
            ),
            notes=(
                "SBA / undying keyword / any_target self-ping physics landed "
                "(Permanent.damage_marked, apply_state_based_actions, seed_grant_undying, "
                "DealDamage any_target). Remaining for promotion: audited Oracle + "
                "Mikaeus grant/anthem compile + gold witness."
            ),
        ),
        OracleGap(
            proposed_gold_id="core_heliod_ballista",
            left_name="Heliod, Sun-Crowned",
            right_name="Walking Ballista",
            blockers=(
                "printed 0/0 Ballista + SBA-safe starting counters (≥2) not used by discovery seed",
                "Heliod lifelink must be a paid {1}{W} activation, not seed_grant_lifelink",
                "seed_grant_lifelink is quarantined from Oracle product VERIFIED",
            ),
            notes=(
                "Audited ORACLE_EXACT fixtures retained for curriculum. "
                "Do not re-promote until two-counter 0/0 start, SBA timing, and paid Heliod "
                "activation verify without seed_grant_lifelink."
            ),
        ),
    ]


__all__ = ["OracleGap", "oracle_gap_catalog"]
