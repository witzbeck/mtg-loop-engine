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
    "Staff of Domination": RealOracleCurriculum(
        name="Staff of Domination",
        types=["Artifact"],
        oracle_text=(
            "{1}: Untap this artifact.\n"
            "{2}, {T}: You gain 1 life.\n"
            "{3}, {T}: Untap target creature.\n"
            "{4}, {T}: Tap target creature.\n"
            "{5}, {T}: Draw a card."
        ),
        notes="M5 activated-artifact slice: parameterized mana+tap activations.",
    ),
    "Basalt Monolith Live": RealOracleCurriculum(
        name="Basalt Monolith",
        types=["Artifact"],
        oracle_text=(
            "This artifact doesn't untap during your untap step.\n"
            "{T}: Add {C}{C}{C}.\n"
            "{3}: Untap this artifact."
        ),
        notes="Live Scryfall wording (doesn't-untap static + this artifact).",
    ),
    "Intruder Alarm Live": RealOracleCurriculum(
        name="Intruder Alarm",
        types=["Enchantment"],
        oracle_text=(
            "Creatures don't untap during their controllers' untap steps.\n"
            "Whenever a creature enters, untap all creatures."
        ),
        notes="Live Scryfall: untap-all on ETB; static is proof-irrelevant.",
    ),
    "Thraben Doomsayer": RealOracleCurriculum(
        name="Thraben Doomsayer",
        types=["Creature", "Human", "Cleric"],
        oracle_text=(
            "{T}: Create a 1/1 white Human creature token.\n"
            "Fateful hour — As long as you have 5 or less life, "
            "other creatures you control get +2/+2."
        ),
        notes="Tap-token; Fateful hour anthem is proof-irrelevant.",
    ),
    "Sanguine Bond": RealOracleCurriculum(
        name="Sanguine Bond",
        types=["Enchantment"],
        oracle_text="Whenever you gain life, target opponent loses that much life.",
    ),
    "Exquisite Blood": RealOracleCurriculum(
        name="Exquisite Blood",
        types=["Enchantment"],
        oracle_text="Whenever an opponent loses life, you gain that much life.",
    ),
    "Vito, Thorn of the Dusk Rose": RealOracleCurriculum(
        name="Vito, Thorn of the Dusk Rose",
        types=["Creature", "Vampire", "Cleric"],
        oracle_text=(
            "Whenever you gain life, target opponent loses that much life.\n"
            "{3}{B}{B}: Creatures you control gain lifelink until end of turn."
        ),
    ),
    # Path a — self-starting COMPLETE unlocks (ETB damage / untap / power mana).
    "Viridian Joiner": RealOracleCurriculum(
        name="Viridian Joiner",
        types=["Creature", "Elf", "Druid"],
        oracle_text="{T}: Add an amount of {G} equal to this creature's power.",
        notes="Power-tap mana; pairs with untappers without external seeds.",
    ),
    "Impact Tremors": RealOracleCurriculum(
        name="Impact Tremors",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature you control enters, "
            "this enchantment deals 1 damage to each opponent."
        ),
        notes="Self-starting ETB damage; token engines can close without life seed.",
    ),
    "Midnight Guard": RealOracleCurriculum(
        name="Midnight Guard",
        types=["Creature", "Human", "Soldier"],
        oracle_text="Whenever another creature enters, untap this creature.",
        notes="ETB untap-self; closes with tap outlets / token makers.",
    ),
    "Witty Roastmaster": RealOracleCurriculum(
        name="Witty Roastmaster",
        types=["Creature", "Devil", "Citizen"],
        oracle_text=(
            "Alliance — Whenever another creature you control enters, "
            "this creature deals 1 damage to each opponent."
        ),
        notes="Ability-word prefix + this-creature ETB damage.",
    ),
    "Warleader's Call": RealOracleCurriculum(
        name="Warleader's Call",
        types=["Enchantment"],
        oracle_text=(
            "Creatures you control get +1/+1.\n"
            "Whenever a creature you control enters, "
            "this enchantment deals 1 damage to each opponent."
        ),
        notes="Anthem is proof-irrelevant; ETB damage is modeled.",
    ),
    "Purphoros, God of the Forge": RealOracleCurriculum(
        name="Purphoros, God of the Forge",
        types=["Enchantment", "Creature", "God"],
        oracle_text=(
            "Indestructible\n"
            "As long as your devotion to red is less than five, Purphoros isn't a creature.\n"
            "Whenever another creature you control enters, Purphoros deals 2 damage to each opponent.\n"
            "{2}{R}: Creatures you control get +1/+0 until end of turn."
        ),
        notes="Devotion/anthem riders proof-irrelevant; ETB damage is the loop engine.",
    ),
    "Presence of Gond": RealOracleCurriculum(
        name="Presence of Gond",
        types=["Enchantment", "Aura"],
        oracle_text=(
            'Enchant creature\n'
            'Enchanted creature has "{T}: Create a 1/1 green Elf Warrior creature token."'
        ),
        notes="Host-tap token grant; pairs with Midnight Guard / Intruder Alarm.",
    ),
    "Aphetto Alchemist": RealOracleCurriculum(
        name="Aphetto Alchemist",
        types=["Creature", "Human", "Wizard"],
        oracle_text=(
            "{T}: Untap target artifact or creature.\n"
            "Morph {U} (You may cast this card face down as a 2/2 creature for {3}. "
            "Turn it face up any time for its morph cost.)"
        ),
        notes="Tap-untap target + Morph proof-irrelevant.",
    ),
}
