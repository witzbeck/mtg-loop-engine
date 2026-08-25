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
    power: int | None = None
    """Printed power when state construction consumes it (ADR 0010)."""
    toughness: int | None = None
    """Printed toughness when state construction consumes it (ADR 0010)."""

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
        oracle_text=(
            "Creatures don't untap during their controllers' untap steps.\n"
            "Whenever a creature enters, untap all creatures."
        ),
        provenance=Provenance.ORACLE_EXACT,
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
        oracle_text="Sacrifice a creature: Add one mana of any color.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:gravecrawler": OracleFixture(
        oracle_id="oracle:gravecrawler",
        name="Gravecrawler",
        types=["Creature", "Zombie"],
        type_line="Creature — Zombie",
        oracle_text=(
            "This creature can't block.\n"
            "You may cast this card from your graveyard as long as you control a Zombie."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:midnight-guard": OracleFixture(
        oracle_id="oracle:midnight-guard",
        name="Midnight Guard",
        types=["Creature", "Human", "Soldier"],
        type_line="Creature — Human Soldier",
        oracle_text="Whenever another creature enters, untap this creature.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:presence-of-gond": OracleFixture(
        oracle_id="oracle:presence-of-gond",
        name="Presence of Gond",
        types=["Enchantment", "Aura"],
        type_line="Enchantment — Aura",
        oracle_text=(
            "Enchant creature\n"
            'Enchanted creature has "{T}: Create a 1/1 green Elf Warrior creature token."'
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:thraben-doomsayer": OracleFixture(
        oracle_id="oracle:thraben-doomsayer",
        name="Thraben Doomsayer",
        types=["Creature", "Human", "Cleric"],
        type_line="Creature — Human Cleric",
        oracle_text=(
            "{T}: Create a 1/1 white Human creature token.\n"
            "Fateful hour — As long as you have 5 or less life, "
            "other creatures you control get +2/+2."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:sanguine-bond": OracleFixture(
        oracle_id="oracle:sanguine-bond",
        name="Sanguine Bond",
        types=["Enchantment"],
        type_line="Enchantment",
        oracle_text="Whenever you gain life, target opponent loses that much life.",
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:exquisite-blood": OracleFixture(
        oracle_id="oracle:exquisite-blood",
        name="Exquisite Blood",
        types=["Enchantment"],
        type_line="Enchantment",
        oracle_text="Whenever an opponent loses life, you gain that much life.",
        provenance=Provenance.ORACLE_EXACT,
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
    "oracle:zirda-the-dawnwaker": OracleFixture(
        oracle_id="oracle:zirda-the-dawnwaker",
        name="Zirda, the Dawnwaker",
        types=["Creature", "Elemental", "Fox"],
        type_line="Legendary Creature — Elemental Fox",
        oracle_text=(
            "Companion — Each permanent card in your starting deck has an activated ability. "
            "(If this card is your chosen companion, you may put it into your hand from outside "
            "the game for {3} as a sorcery.)\n"
            "Abilities you activate that aren't mana abilities cost {2} less to activate. "
            "This effect can't reduce the mana in that cost to less than one mana.\n"
            "{1}, {T}: Target creature can't block this turn."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:devoted-druid": OracleFixture(
        oracle_id="oracle:devoted-druid",
        name="Devoted Druid",
        types=["Creature", "Elf", "Druid"],
        type_line="Creature — Elf Druid",
        oracle_text=(
            "{T}: Add {G}.\n"
            "Put a -1/-1 counter on this creature: Untap this creature."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:vizier-of-remedies": OracleFixture(
        oracle_id="oracle:vizier-of-remedies",
        name="Vizier of Remedies",
        types=["Creature", "Human", "Cleric"],
        type_line="Creature — Human Cleric",
        oracle_text=(
            "If one or more -1/-1 counters would be put on a creature you control, "
            "that many -1/-1 counters minus one are put on it instead."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:rosie-cotton-of-south-lane": OracleFixture(
        oracle_id="oracle:rosie-cotton-of-south-lane",
        name="Rosie Cotton of South Lane",
        types=["Creature", "Halfling", "Peasant"],
        type_line="Legendary Creature — Halfling Peasant",
        oracle_text=(
            "When Rosie Cotton enters, create a Food token. "
            '(It\'s an artifact with "{2}, {T}, Sacrifice this token: You gain 3 life.")\n'
            "Whenever you create a token, put a +1/+1 counter on target creature "
            "you control other than Rosie Cotton."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:scurry-oak": OracleFixture(
        oracle_id="oracle:scurry-oak",
        name="Scurry Oak",
        types=["Creature", "Treefolk"],
        type_line="Creature — Treefolk",
        oracle_text=(
            "Evolve (Whenever a creature you control enters, if that creature has "
            "greater power or toughness than this creature, put a +1/+1 counter "
            "on this creature.)\n"
            "Whenever one or more +1/+1 counters are put on this creature, "
            "you may create a 1/1 green Squirrel creature token."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:heliod-sun-crowned": OracleFixture(
        oracle_id="oracle:heliod-sun-crowned",
        name="Heliod, Sun-Crowned",
        types=["Enchantment", "Creature", "God"],
        type_line="Legendary Enchantment Creature — God",
        oracle_text=(
            "Indestructible\n"
            "As long as your devotion to white is less than five, Heliod isn't a creature.\n"
            "Whenever you gain life, put a +1/+1 counter on target creature or "
            "enchantment you control.\n"
            "{1}{W}: Another target creature gains lifelink until end of turn."
        ),
        provenance=Provenance.ORACLE_EXACT,
    ),
    "oracle:walking-ballista": OracleFixture(
        oracle_id="oracle:walking-ballista",
        name="Walking Ballista",
        types=["Artifact", "Creature", "Construct"],
        type_line="Artifact Creature — Construct",
        oracle_text=(
            "This creature enters with X +1/+1 counters on it.\n"
            "{4}: Put a +1/+1 counter on this creature.\n"
            "Remove a +1/+1 counter from this creature: It deals 1 damage to any target."
        ),
        provenance=Provenance.ORACLE_EXACT,
        power=0,
        toughness=0,
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
