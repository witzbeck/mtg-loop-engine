"""Gold Oracle / physics fixtures with ADR 0007 provenance.

``ORACLE_EXACT`` entries must match committed audited source records under
``semantics/audited/records/``. ``ORACLE_DIVERGENT`` is a migration quarantine
allowlisted in ``provenance.FROZEN_ORACLE_DIVERGENT_IDS``.
"""

from __future__ import annotations

from dataclasses import dataclass

from mtg_loop_engine.semantics.enums import Provenance


@dataclass(frozen=True)
class OracleFixture:
    oracle_id: str
    name: str
    types: list[str]
    oracle_text: str
    provenance: Provenance
    type_line: str = ""
    """Optional audited type line; defaults to ``" ".join(types)`` when empty."""

    @property
    def is_fixture(self) -> bool:
        """Deprecated alias: True iff SYNTHETIC. Prefer ``provenance``."""
        return self.provenance is Provenance.SYNTHETIC


GOLD_ORACLE_FIXTURES: dict[str, OracleFixture] = {
    "oracle:basalt-monolith": OracleFixture(
        oracle_id="oracle:basalt-monolith",
        name="Basalt Monolith",
        types=["Artifact"],
        type_line="Artifact",
        oracle_text="{T}: Add {C}{C}{C}.\n{3}: Untap Basalt Monolith.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "synthetic:generic-activated-cost-reducer": OracleFixture(
        oracle_id="synthetic:generic-activated-cost-reducer",
        name="Synthetic Cost Reducer",
        types=["Enchantment"],
        type_line="Enchantment",
        oracle_text="Activated abilities you control cost {1} less to activate.",
        provenance=Provenance.SYNTHETIC,
    ),
    "oracle:intruder-alarm": OracleFixture(
        oracle_id="oracle:intruder-alarm",
        name="Intruder Alarm",
        types=["Enchantment"],
        type_line="Enchantment",
        # Real Oracle also has the don't-untap static; simplified → quarantine.
        oracle_text="Whenever a creature enters the battlefield, untap target permanent.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "synthetic:token-tapper": OracleFixture(
        oracle_id="synthetic:token-tapper",
        name="Eager Apprentice",
        types=["Creature"],
        type_line="Creature",
        oracle_text="{T}: Create a 1/1 Homunculus creature token.",
        provenance=Provenance.SYNTHETIC,
    ),
    "oracle:phyrexian-altar": OracleFixture(
        oracle_id="oracle:phyrexian-altar",
        name="Phyrexian Altar",
        types=["Artifact"],
        type_line="Artifact",
        # Real Oracle: any color. Tuned black → quarantine.
        oracle_text="Sacrifice a creature: Add {B}.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "oracle:gravecrawler": OracleFixture(
        oracle_id="oracle:gravecrawler",
        name="Gravecrawler",
        types=["Creature"],
        type_line="Creature — Zombie",
        # Activated return ≠ cast-from-GY + Zombie restriction → quarantine.
        oracle_text="{B}: Return Gravecrawler from your graveyard to the battlefield.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "synthetic:persistent-phoenix": OracleFixture(
        oracle_id="synthetic:persistent-phoenix",
        name="Persistent Phoenix",
        types=["Creature"],
        type_line="Creature",
        oracle_text="Whenever Persistent Phoenix dies, return it to the battlefield.",
        provenance=Provenance.SYNTHETIC,
    ),
    "oracle:viscera-seer": OracleFixture(
        oracle_id="oracle:viscera-seer",
        name="Viscera Seer",
        types=["Creature"],
        type_line="Creature — Vampire Wizard",
        oracle_text="Sacrifice a creature: Scry 1.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:blood-artist": OracleFixture(
        oracle_id="oracle:blood-artist",
        name="Blood Artist",
        types=["Creature"],
        type_line="Creature — Vampire",
        # Real Oracle also gains life and targets; simplified → quarantine.
        oracle_text="Whenever a creature dies, each opponent loses 1 life.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "synthetic:scaled-gun": OracleFixture(
        oracle_id="synthetic:scaled-gun",
        name="Scaled Gun",
        types=["Artifact"],
        type_line="Artifact",
        oracle_text=(
            "Remove a +1/+1 counter from this permanent: "
            "It deals 1 damage to target opponent."
        ),
        provenance=Provenance.SYNTHETIC,
    ),
    "synthetic:put-counter-activated": OracleFixture(
        oracle_id="synthetic:put-counter-activated",
        name="Synthetic Put-Counter Activated",
        types=["Enchantment"],
        type_line="Enchantment",
        oracle_text="Put a +1/+1 counter on target permanent.",
        provenance=Provenance.SYNTHETIC,
    ),
    "oracle:reassembling-skeleton": OracleFixture(
        oracle_id="oracle:reassembling-skeleton",
        name="Reassembling Skeleton",
        types=["Creature"],
        type_line="Creature — Skeleton Warrior",
        # Real cost/return-tapped semantics differ → quarantine.
        oracle_text="{1}: Return Reassembling Skeleton from your graveyard to the battlefield.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "oracle:ashnods-altar": OracleFixture(
        oracle_id="oracle:ashnods-altar",
        name="Ashnod's Altar",
        types=["Artifact"],
        type_line="Artifact",
        oracle_text="Sacrifice a creature: Add {C}{C}.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:rest-in-peace": OracleFixture(
        oracle_id="oracle:rest-in-peace",
        name="Rest in Peace",
        types=["Enchantment"],
        type_line="Enchantment",
        # Real Oracle: any card from anywhere; creature-only → quarantine.
        oracle_text="If a creature would die, exile it instead.",
        provenance=Provenance.ORACLE_DIVERGENT,
    ),
    "synthetic:etb-ping": OracleFixture(
        oracle_id="synthetic:etb-ping",
        name="Impact Tremors Lite",
        types=["Enchantment"],
        type_line="Enchantment",
        oracle_text=(
            "Whenever a creature enters the battlefield, "
            "Impact Tremors Lite deals 1 damage to each opponent."
        ),
        provenance=Provenance.SYNTHETIC,
    ),
    "synthetic:self-untap-tapper": OracleFixture(
        oracle_id="synthetic:self-untap-tapper",
        name="Perpetual Apprentice",
        types=["Creature"],
        type_line="Creature",
        oracle_text=(
            "{T}: Create a 1/1 Homunculus creature token. "
            "Untap Perpetual Apprentice."
        ),
        provenance=Provenance.SYNTHETIC,
    ),
    "oracle:soul-warden": OracleFixture(
        oracle_id="oracle:soul-warden",
        name="Soul Warden",
        types=["Creature"],
        type_line="Creature — Human Cleric",
        oracle_text="Whenever another creature enters the battlefield, you gain 1 life.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "synthetic:suicidal-phoenix": OracleFixture(
        oracle_id="synthetic:suicidal-phoenix",
        name="Ember Phoenix",
        types=["Creature"],
        type_line="Creature",
        oracle_text=(
            "Sacrifice Ember Phoenix:\n"
            "Whenever Ember Phoenix dies, return it to the battlefield."
        ),
        provenance=Provenance.SYNTHETIC,
    ),
    "synthetic:token-breeder": OracleFixture(
        oracle_id="synthetic:token-breeder",
        name="Token Breeder",
        types=["Creature"],
        type_line="Creature",
        oracle_text=(
            "{T}, Sacrifice a creature token: Create two 1/1 Spawn creature tokens."
        ),
        provenance=Provenance.SYNTHETIC,
    ),
}


UNSUPPORTED_FIXTURE = OracleFixture(
    oracle_id="oracle:isochron-scepter",
    name="Isochron Scepter",
    types=["Artifact"],
    type_line="Artifact",
    oracle_text=(
        "Imprint — When Isochron Scepter enters, you may exile an instant card "
        "with mana value 2 or less from your hand.\n"
        "{2}, {T}: You may copy the exiled card. If you do, you may cast the copy "
        "without paying its mana cost."
    ),
    provenance=Provenance.ORACLE_DIVERGENT,
)
