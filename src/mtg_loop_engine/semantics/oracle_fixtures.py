"""Canonical Oracle-text fixtures for gold_core compiler regression."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OracleFixture:
    oracle_id: str
    name: str
    types: list[str]
    oracle_text: str


# Wording is intentionally close to real Oracle, tuned to deterministic patterns.
GOLD_ORACLE_FIXTURES: dict[str, OracleFixture] = {
    "oracle:basalt-monolith": OracleFixture(
        oracle_id="oracle:basalt-monolith",
        name="Basalt Monolith",
        types=["Artifact"],
        oracle_text="{T}: Add {C}{C}{C}.\n{3}: Untap Basalt Monolith.",
    ),
    "oracle:training-grounds": OracleFixture(
        oracle_id="oracle:training-grounds",
        name="Training Grounds",
        types=["Enchantment"],
        oracle_text="Activated abilities you control cost {1} less to activate.",
    ),
    "oracle:intruder-alarm": OracleFixture(
        oracle_id="oracle:intruder-alarm",
        name="Intruder Alarm",
        types=["Enchantment"],
        oracle_text="Whenever a creature enters the battlefield, untap target permanent.",
    ),
    "oracle:token-tapper": OracleFixture(
        oracle_id="oracle:token-tapper",
        name="Eager Apprentice",
        types=["Creature"],
        oracle_text="{T}: Create a 1/1 Homunculus creature token.",
    ),
    "oracle:phyrexian-altar": OracleFixture(
        oracle_id="oracle:phyrexian-altar",
        name="Phyrexian Altar",
        types=["Artifact"],
        oracle_text="Sacrifice a creature: Add {B}.",
    ),
    "oracle:gravecrawler": OracleFixture(
        oracle_id="oracle:gravecrawler",
        name="Gravecrawler",
        types=["Creature"],
        oracle_text="{B}: Return Gravecrawler from your graveyard to the battlefield.",
    ),
    "oracle:phoenix": OracleFixture(
        oracle_id="oracle:phoenix",
        name="Persistent Phoenix",
        types=["Creature"],
        oracle_text="Whenever Persistent Phoenix dies, return it to the battlefield.",
    ),
    "oracle:viscera-seer": OracleFixture(
        oracle_id="oracle:viscera-seer",
        name="Viscera Seer",
        types=["Creature"],
        oracle_text="Sacrifice a creature: Scry 1.",
    ),
    "oracle:blood-artist": OracleFixture(
        oracle_id="oracle:blood-artist",
        name="Blood Artist",
        types=["Creature"],
        oracle_text="Whenever a creature dies, each opponent loses 1 life.",
    ),
    "oracle:scaled-gun": OracleFixture(
        oracle_id="oracle:scaled-gun",
        name="Scaled Gun",
        types=["Artifact"],
        oracle_text="Remove a +1/+1 counter from this permanent: It deals 1 damage to target opponent.",
    ),
    "oracle:hardened-scales": OracleFixture(
        oracle_id="oracle:hardened-scales",
        name="Hardened Scales",
        types=["Enchantment"],
        # Modeled as explicit put-counter activated for M2 pattern coverage.
        oracle_text="Put a +1/+1 counter on target permanent.",
    ),
    "oracle:reassembling-skeleton": OracleFixture(
        oracle_id="oracle:reassembling-skeleton",
        name="Reassembling Skeleton",
        types=["Creature"],
        oracle_text="{1}: Return Reassembling Skeleton from your graveyard to the battlefield.",
    ),
    "oracle:ashnods-altar": OracleFixture(
        oracle_id="oracle:ashnods-altar",
        name="Ashnod's Altar",
        types=["Artifact"],
        oracle_text="Sacrifice a creature: Add {C}{C}.",
    ),
    "oracle:rest-in-peace": OracleFixture(
        oracle_id="oracle:rest-in-peace",
        name="Rest in Peace",
        types=["Enchantment"],
        oracle_text="If a creature would die, exile it instead.",
    ),
    "oracle:etb-ping": OracleFixture(
        oracle_id="oracle:etb-ping",
        name="Impact Tremors Lite",
        types=["Enchantment"],
        oracle_text="Whenever a creature enters the battlefield, Impact Tremors Lite deals 1 damage to each opponent.",
    ),
    "oracle:self-untap-tapper": OracleFixture(
        oracle_id="oracle:self-untap-tapper",
        name="Perpetual Apprentice",
        types=["Creature"],
        oracle_text="{T}: Create a 1/1 Homunculus creature token. Untap Perpetual Apprentice.",
    ),
    "oracle:soul-warden": OracleFixture(
        oracle_id="oracle:soul-warden",
        name="Soul Warden",
        types=["Creature"],
        oracle_text="Whenever another creature enters the battlefield, you gain 1 life.",
    ),
    "oracle:suicidal-phoenix": OracleFixture(
        oracle_id="oracle:suicidal-phoenix",
        name="Ember Phoenix",
        types=["Creature"],
        oracle_text=(
            "Sacrifice Ember Phoenix:\n"
            "Whenever Ember Phoenix dies, return it to the battlefield."
        ),
    ),
    "oracle:token-breeder": OracleFixture(
        oracle_id="oracle:token-breeder",
        name="Token Breeder",
        types=["Creature"],
        oracle_text="{T}, Sacrifice a creature token: Create two 1/1 Spawn creature tokens.",
    ),
}


UNSUPPORTED_FIXTURE = OracleFixture(
    oracle_id="oracle:isochron-scepter",
    name="Isochron Scepter",
    types=["Artifact"],
    oracle_text=(
        "Imprint — When Isochron Scepter enters, you may exile an instant card "
        "with mana value 2 or less from your hand.\n"
        "{2}, {T}: You may copy the exiled card. If you do, you may cast the copy "
        "without paying its mana cost."
    ),
)
