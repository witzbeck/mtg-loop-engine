"""Real Oracle curriculum snippets for M4 compiler expansion tests and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealOracleCurriculum:
    name: str
    types: list[str]
    oracle_text: str
    notes: str = ""


# Live wording from Scryfall oracle_cards bulk (local snapshot), except where noted.
REAL_ORACLE_CURRICULUM: dict[str, RealOracleCurriculum] = {
    "Gravecrawler": RealOracleCurriculum(
        name="Gravecrawler",
        types=["Creature", "Zombie"],
        oracle_text=(
            "This creature can't block.\n"
            "You may cast this card from your graveyard as long as you control a Zombie."
        ),
        notes=(
            "Post-errata Scryfall text: cast-from-GY + Zombie gate. Modeled as GY→BF "
            "activation with {B} cost and generic Zombie fodder (ADR 0002)."
        ),
    ),
    # Pre-errata activated return — keeps zone-recursion pattern/rediscovery seam testable
    # without claiming current Scryfall Gravecrawler rediscovers today.
    "GravecrawlerActivatedReturn": RealOracleCurriculum(
        name="Gravecrawler",
        types=["Creature", "Zombie"],
        oracle_text=(
            "Creatures with power 2 or less can't block Gravecrawler.\n"
            "{B}: Return Gravecrawler from your graveyard to the battlefield.\n"
            "You may cast Gravecrawler only from your graveyard."
        ),
        notes="Curriculum stand-in for activated GY return (historical Oracle shape).",
    ),
    "Phyrexian Altar": RealOracleCurriculum(
        name="Phyrexian Altar",
        types=["Artifact"],
        oracle_text="Sacrifice a creature: Add one mana of any color.",
    ),
    "Reassembling Skeleton": RealOracleCurriculum(
        name="Reassembling Skeleton",
        types=["Creature", "Skeleton"],
        oracle_text=(
            "{1}{B}: Return this card from your graveyard to the battlefield tapped.\n"
            "Activate only as a sorcery."
        ),
        notes="Mana sink {1}{B} does not close with a single any-color from Altar alone.",
    ),
    "Freed from the Real": RealOracleCurriculum(
        name="Freed from the Real",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            "{U}: Tap enchanted creature.\n"
            "{U}: Untap enchanted creature."
        ),
        notes="M5 aura-channel slice: tap/untap enchanted as target_permanent.",
    ),
    "Pemmin's Aura": RealOracleCurriculum(
        name="Pemmin's Aura",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            "{U}: Untap enchanted creature.\n"
            "{U}: Enchanted creature gains flying until end of turn.\n"
            "{U}: Enchanted creature gains shroud until end of turn. "
            "(It can't be the target of spells or abilities.)\n"
            "{1}: Enchanted creature gets +1/-1 or -1/+1 until end of turn."
        ),
        notes="Untap is modeled; keyword/pump riders are proof-irrelevant.",
    ),
}
