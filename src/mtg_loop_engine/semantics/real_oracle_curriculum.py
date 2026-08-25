"""Real Oracle curriculum snippets for M4 compiler expansion tests and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealOracleCurriculum:
    name: str
    types: list[str]
    oracle_text: str


# Wording aligned with Scryfall oracle_cards bulk (2026-08-24 snapshot).
REAL_ORACLE_CURRICULUM: dict[str, RealOracleCurriculum] = {
    "Gravecrawler": RealOracleCurriculum(
        name="Gravecrawler",
        types=["Creature", "Zombie"],
        oracle_text=(
            "Creatures with power 2 or less can't block Gravecrawler.\n"
            "{B}: Return Gravecrawler from your graveyard to the battlefield.\n"
            "You may cast Gravecrawler only from your graveyard."
        ),
    ),
    "Phyrexian Altar": RealOracleCurriculum(
        name="Phyrexian Altar",
        types=["Artifact"],
        oracle_text="Sacrifice a creature: Add one mana of any color to your mana pool.",
    ),
    "Reassembling Skeleton": RealOracleCurriculum(
        name="Reassembling Skeleton",
        types=["Creature", "Skeleton"],
        oracle_text=(
            "{1}{B}: Return Reassembling Skeleton from your graveyard to the battlefield.\n"
            "Activate only as a sorcery."
        ),
    ),
}
