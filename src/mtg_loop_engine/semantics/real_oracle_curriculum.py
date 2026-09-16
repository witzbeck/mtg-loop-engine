"""Real Oracle curriculum snippets for M4 compiler expansion tests and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealOracleCurriculum:
    name: str
    types: list[str]
    oracle_text: str
    notes: str = ""
    colors: tuple[str, ...] = ()
    mana_cost: str | None = None
    mana_value: int | None = None


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
    "Bloodchief Ascension": RealOracleCurriculum(
        name="Bloodchief Ascension",
        types=["Enchantment"],
        oracle_text=(
            "At the beginning of each end step, if an opponent lost 2 or more life "
            "this turn, you may put a quest counter on Bloodchief Ascension.\n"
            'Enchantments you control have "Whenever a card is put into an opponent\'s '
            'graveyard from anywhere, that player loses 2 life."'
        ),
        notes="Granted graveyard-drain static; quest counter proof-irrelevant.",
    ),
    "Mindcrank": RealOracleCurriculum(
        name="Mindcrank",
        types=["Artifact"],
        oracle_text="Whenever an opponent loses life, that player mills a card.",
        notes="Loss-to-mill feedback with Bloodchief Ascension (1-card model for Path-a).",
        mana_cost="{2}",
        mana_value=2,
    ),
    "Mindcrank Scaled": RealOracleCurriculum(
        name="Mindcrank",
        types=["Artifact"],
        oracle_text=(
            "Whenever an opponent loses life, that player mills that many cards. "
            "(Damage causes loss of life.)"
        ),
        notes="E17: scaled life-loss mill (Spellbook Oracle wording).",
        mana_cost="{2}",
        mana_value=2,
    ),
    "Keening Stone": RealOracleCurriculum(
        name="Keening Stone",
        types=["Artifact"],
        oracle_text=(
            "{5}, {T}: Target player mills X cards, where X is the number of cards in that "
            "player's graveyard."
        ),
        notes="E17: mill = opponent GY count.",
        mana_cost="{6}",
        mana_value=6,
    ),
    "Bruvac the Grandiloquent": RealOracleCurriculum(
        name="Bruvac the Grandiloquent",
        types=["Legendary", "Creature", "Human", "Advisor"],
        oracle_text=(
            "If an opponent would mill one or more cards, they mill twice that many cards "
            "instead. (To mill a card, a player puts the top card of their library into "
            "their graveyard.)"
        ),
        notes="E17: ReplacementDoubleMill.",
        colors=("U",),
        mana_cost="{2}{U}",
        mana_value=3,
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
    # Path a — slice 7: life-untap / self-ETB untap-all / counter-mana / ETB may-untap.
    "Famished Paladin": RealOracleCurriculum(
        name="Famished Paladin",
        types=["Creature", "Vampire", "Knight"],
        oracle_text=(
            "This creature doesn't untap during your untap step.\n"
            "Whenever you gain life, untap this creature."
        ),
        notes="Life-gain untap; doesn't-untap static is proof-irrelevant.",
    ),
    "Village Bell-Ringer": RealOracleCurriculum(
        name="Village Bell-Ringer",
        types=["Creature", "Human", "Scout"],
        oracle_text=(
            "Flash (You may cast this spell any time you could cast an instant.)\n"
            "When this creature enters, untap all creatures you control."
        ),
        notes="Self-ETB untap-all; Flash reminder is proof-irrelevant.",
        colors=("W",),
        mana_cost="{2}{W}",
        mana_value=3,
    ),
    "Gyre Sage": RealOracleCurriculum(
        name="Gyre Sage",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "Evolve (Whenever a creature you control enters, if that creature has "
            "greater power or toughness than this creature, put a +1/+1 counter "
            "on this creature.)\n"
            "{T}: Add {G} for each +1/+1 counter on this creature."
        ),
        notes="Counter-scaled tap mana; Evolve reminder is proof-irrelevant.",
    ),
    "Pestermite": RealOracleCurriculum(
        name="Pestermite",
        types=["Creature", "Faerie", "Rogue"],
        oracle_text=(
            "Flash\n"
            "Flying\n"
            "When this creature enters, you may tap or untap target permanent."
        ),
        notes="Combo-favorable: ETB may tap-or-untap modeled as untap target.",
    ),
    # Path a — slice 9: scaled tap-mana (frontier P0 cluster).
    "Bloom Tender": RealOracleCurriculum(
        name="Bloom Tender",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "Vivid — {T}: For each color among permanents you control, "
            "add one mana of that color."
        ),
        notes="Vivid multi-color tap mana; pairs with untappers (frontier P0).",
    ),
    "Sanctum Weaver": RealOracleCurriculum(
        name="Sanctum Weaver",
        types=["Creature", "Dryad", "Druid"],
        oracle_text=(
            "{T}: Add X mana of any one color, where X is the number of "
            "enchantments you control."
        ),
        notes="Enchantment-count scaled mana (frontier P0).",
    ),
    "Axebane Guardian": RealOracleCurriculum(
        name="Axebane Guardian",
        types=["Creature", "Human", "Shaman"],
        oracle_text=(
            "Defender\n"
            "{T}: Add X mana in any combination of colors, where X is the "
            "number of creatures you control with defender."
        ),
        notes="Defender-count any-color mana.",
    ),
    "Circle of Dreams Druid": RealOracleCurriculum(
        name="Circle of Dreams Druid",
        types=["Creature", "Human", "Druid"],
        oracle_text="{T}: Add {G} for each creature you control.",
        notes="Creature-count green mana (frontier P0).",
    ),
    "Priest of Titania": RealOracleCurriculum(
        name="Priest of Titania",
        types=["Creature", "Elf", "Druid"],
        oracle_text="{T}: Add {G} for each Elf on the battlefield.",
        notes="Battlefield Elf count (frontier P0).",
    ),
    "Overgrown Battlement": RealOracleCurriculum(
        name="Overgrown Battlement",
        types=["Creature", "Wall"],
        oracle_text=(
            "Defender\n"
            "{T}: Add {G} for each creature you control with defender."
        ),
        notes="Defender-count green mana.",
    ),
    "Karametra's Acolyte": RealOracleCurriculum(
        name="Karametra's Acolyte",
        types=["Creature", "Human", "Druid"],
        oracle_text=(
            "{T}: Add an amount of {G} equal to your devotion to green. "
            "(Each {G} in the mana costs of permanents you control counts "
            "toward your devotion to green.)"
        ),
        notes="Devotion-scaled green; reminder clause is separate.",
    ),
    "Elvish Archdruid": RealOracleCurriculum(
        name="Elvish Archdruid",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "Other Elf creatures you control get +1/+1.\n"
            "{T}: Add {G} for each Elf you control."
        ),
        notes="Elf-count green; anthem proof-irrelevant.",
    ),
    "Umbral Mantle": RealOracleCurriculum(
        name="Umbral Mantle",
        types=["Artifact", "Equipment"],
        oracle_text=(
            'Equipped creature has "{3}, {Q}: This creature gets +2/+2 until end of turn." '
            "({Q} is the untap symbol.)\n"
            "Equip {0}"
        ),
        notes="Frontier P1 slice 10: {Q} untap-symbol cost + host activation; pairs with tap-mana dorks.",
    ),
    "Mana Reflection": RealOracleCurriculum(
        name="Mana Reflection",
        types=["Enchantment"],
        oracle_text=(
            "If you tap a permanent for mana, it produces twice as much of that mana instead."
        ),
        notes="Frontier P1 slice 11: 2× tap-mana replacement.",
    ),
    "Nyxbloom Ancient": RealOracleCurriculum(
        name="Nyxbloom Ancient",
        types=["Enchantment", "Creature"],
        oracle_text=(
            "Trample\n"
            "If you tap a permanent for mana, it produces three times as much of that mana instead."
        ),
        notes="Frontier P1 slice 11: 3× tap-mana replacement; Trample proof-irrelevant.",
    ),
    "Kami of Whispered Hopes": RealOracleCurriculum(
        name="Kami of Whispered Hopes",
        types=["Creature", "Spirit"],
        oracle_text=(
            "If one or more +1/+1 counters would be put on a permanent you control, "
            "that many plus one +1/+1 counters are put on that permanent instead.\n"
            "{T}: Add X mana of any one color, where X is this creature's power."
        ),
        notes=(
            "Frontier P0 slice 12: +1/+1 put amplify + power-scaled any-color mana "
            "(4 pair unlocks vs Storm Herd 5 one-shot / Wirewood Channeler 2)."
        ),
    ),
    "Light of Promise": RealOracleCurriculum(
        name="Light of Promise",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            'Enchanted creature has "Whenever you gain life, put that many '
            '+1/+1 counters on this creature."'
        ),
        notes=(
            "Frontier P0 slice 13: life→that-many p1p1 on enchanted host "
            "(2 cards / 3 pair unlocks; Ballista / Triskelion)."
        ),
    ),
    "Sunbond": RealOracleCurriculum(
        name="Sunbond",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            'Enchanted creature has "Whenever you gain life, put that many '
            '+1/+1 counters on this creature."'
        ),
        notes="Same granted trigger as Light of Promise (slice 13).",
    ),
    "Archangel of Thune": RealOracleCurriculum(
        name="Archangel of Thune",
        types=["Creature", "Angel"],
        oracle_text=(
            "Flying\n"
            "Lifelink (Damage dealt by this creature also causes you to gain "
            "that much life.)\n"
            "Whenever you gain life, put a +1/+1 counter on each creature you control."
        ),
        notes="Frontier P0 slice 14: GAIN_LIFE → each controlled creature p1p1.",
    ),
    "Cathars' Crusade": RealOracleCurriculum(
        name="Cathars' Crusade",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature you control enters, put a +1/+1 counter on each "
            "creature you control."
        ),
        notes="Frontier P0 slice 15: controlled-creature ETB → each creature p1p1.",
    ),
    "Heronblade Elite": RealOracleCurriculum(
        name="Heronblade Elite",
        types=["Creature", "Human", "Warrior"],
        oracle_text=(
            "Vigilance\n"
            "Whenever another Human you control enters, put a +1/+1 counter on "
            "this creature.\n"
            "{T}: Add X mana of any one color, where X is this creature's power."
        ),
        notes=(
            "Frontier P0 slice 16: Human ETB → self p1p1 + power-scaled any-color mana "
            "(Staff / Mantle unlocks)."
        ),
    ),
    "Sliver Queen": RealOracleCurriculum(
        name="Sliver Queen",
        types=["Legendary", "Creature", "Sliver"],
        oracle_text="{2}: Create a 1/1 colorless Sliver creature token.",
        notes=(
            "Frontier P0 slice 17: mana-activated token create "
            "(2 pair unlocks vs Intruder Alarm / Ashnod-class; reject Storm Herd)."
        ),
    ),
    "South Wind Avatar": RealOracleCurriculum(
        name="South Wind Avatar",
        types=["Creature", "Snake", "Spirit", "Avatar"],
        oracle_text=(
            "Deathtouch\n"
            "Whenever another creature you control dies, you gain life equal "
            "to its toughness.\n"
            "Whenever you gain life, each opponent loses 1 life."
        ),
        notes=(
            "Frontier P0 slice 18: dies→life=toughness + fixed drain on gain life "
            "(2 unlocks vs Exquisite-class)."
        ),
    ),
    "Shrieking Drake": RealOracleCurriculum(
        name="Shrieking Drake",
        types=["Creature", "Drake"],
        oracle_text=(
            "Flying\n"
            "When this creature enters, return a creature you control to "
            "its owner's hand."
        ),
        notes=(
            "Frontier P1 slices 19–20: ETB bounce; slices 24–25 rediscovery via "
            "cast-from-hand + Aluren."
        ),
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Whitemane Lion": RealOracleCurriculum(
        name="Whitemane Lion",
        types=["Creature", "Cat"],
        oracle_text=(
            "Flash\n"
            "When this creature enters, return a creature you control to "
            "its owner's hand."
        ),
        notes="Same ETB bounce as Shrieking Drake (Flash irrelevant).",
        colors=("W",),
        mana_cost="{1}{W}",
        mana_value=2,
    ),
    "Ivy Lane Denizen": RealOracleCurriculum(
        name="Ivy Lane Denizen",
        types=["Creature", "Elf", "Warrior"],
        oracle_text=(
            "Whenever another green creature you control enters, put a +1/+1 "
            "counter on target creature."
        ),
        notes=(
            "Frontier P0 slice 21: green color filter on ETB + target p1p1 "
            "(2 unlocks; colors on Permanent/CardSemantics)."
        ),
        colors=("G",),
    ),
    "Power Artifact": RealOracleCurriculum(
        name="Power Artifact",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant artifact\n"
            "Enchanted artifact's activated abilities cost {2} less to activate. "
            "This effect can't reduce the mana in that cost to less than one mana."
        ),
        notes="Frontier P1 slice 22: enchanted-artifact activate −{2} (floor 1).",
    ),
    "Mesmeric Orb": RealOracleCurriculum(
        name="Mesmeric Orb",
        types=["Artifact"],
        oracle_text=(
            "Whenever a permanent becomes untapped, that permanent's controller "
            "mills a card."
        ),
        notes="Frontier P1 slice 23: UNTAP → self-mill (Basalt / Aphetto pairs).",
    ),
    "Aluren": RealOracleCurriculum(
        name="Aluren",
        types=["Enchantment"],
        oracle_text=(
            "Any player may cast creature spells with mana value 3 or less "
            "without paying their mana costs and as though they had flash."
        ),
        notes=(
            "Slice 24–25: free cast MV≤3; Drake/Lion rediscovery path-a."
        ),
        colors=("G",),
        mana_cost="{2}{G}{G}",
        mana_value=4,
    ),
    "Banishing Knack": RealOracleCurriculum(
        name="Banishing Knack",
        types=["Instant"],
        oracle_text=(
            'Until end of turn, target creature gains '
            '"{T}: Return target nonland permanent to its owner\'s hand."'
        ),
        notes=(
            "Slice 24–25: Instant grant tap-bounce (witness-persistent setup)."
        ),
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Retraction Helix": RealOracleCurriculum(
        name="Retraction Helix",
        types=["Instant"],
        oracle_text=(
            'Until end of turn, target creature gains '
            '"{T}: Return target nonland permanent to its owner\'s hand."'
        ),
        notes="Same Instant grant as Banishing Knack.",
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Fleetfoot Panther": RealOracleCurriculum(
        name="Fleetfoot Panther",
        types=["Creature", "Cat"],
        oracle_text=(
            "Flash\n"
            "When this creature enters, return a green or white creature you "
            "control to its owner's hand."
        ),
        notes="Slice 26: ETB bounce green-or-white creature; Aluren rediscovery.",
        colors=("G", "W"),
        mana_cost="{1}{G}{W}",
        mana_value=3,
    ),
    "Dream Stalker": RealOracleCurriculum(
        name="Dream Stalker",
        types=["Creature", "Illusion"],
        oracle_text=(
            "When this creature enters, return a permanent you control to "
            "its owner's hand."
        ),
        notes="Slice 27: ETB bounce any controlled permanent; Alarm rediscovery.",
        colors=("U",),
        mana_cost="{1}{U}",
        mana_value=2,
    ),
    "Ancestral Statue": RealOracleCurriculum(
        name="Ancestral Statue",
        types=["Artifact", "Creature", "Golem"],
        oracle_text=(
            "When this creature enters, return a nonland permanent you control "
            "to its owner's hand."
        ),
        notes="Slice 28: ETB bounce controlled nonland; Alarm + mana-dork pay {4}.",
        mana_cost="{4}",
        mana_value=4,
    ),
    "Temur Sabertooth": RealOracleCurriculum(
        name="Temur Sabertooth",
        types=["Creature", "Cat"],
        oracle_text=(
            "{1}{G}: You may return another creature you control to its owner's "
            "hand. If you do, this creature gains indestructible until end of turn."
        ),
        notes=(
            "Slice 29: paid bounce other creature; indestructible rider "
            "proof-irrelevant. Rediscovery with Village Bell-Ringer + mana dorks."
        ),
        colors=("G",),
        mana_cost="{2}{G}{G}",
        mana_value=4,
    ),
    "Cloudstone Curio": RealOracleCurriculum(
        name="Cloudstone Curio",
        types=["Artifact"],
        oracle_text=(
            "Whenever a nonartifact permanent you control enters, you may return "
            "another permanent you control that shares a permanent type with it "
            "to its owner's hand."
        ),
        notes=(
            "Slice 30: nonartifact ETB → bounce another sharing a permanent type; "
            "Aluren rediscovery with generic creature seeds. Tidespout deferred "
            "(needs CAST + non-creature cast path)."
        ),
        mana_cost="{3}",
        mana_value=3,
    ),
    "Mana Echoes": RealOracleCurriculum(
        name="Mana Echoes",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature enters, you may add an amount of {C} equal to "
            "the number of creatures you control that share a creature type with it."
        ),
        notes=(
            "Slice 32: ETB → {C} × controlled sharing creature type; "
            "Sliver Queen rediscovery with {2} mana seed for first create."
        ),
        colors=("R",),
        mana_cost="{2}{R}{R}",
        mana_value=4,
    ),
    "Earthcraft": RealOracleCurriculum(
        name="Earthcraft",
        types=["Enchantment"],
        oracle_text="Tap an untapped creature you control: Untap target basic land.",
        notes=(
            "Slice 33: tap-creature cost → untap basic land; hold priority with "
            "Drake ETB bounce; basic Island seed."
        ),
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Wirewood Channeler": RealOracleCurriculum(
        name="Wirewood Channeler",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "{T}: Add X mana of any one color, where X is the number of Elves "
            "on the battlefield."
        ),
        notes=(
            "Slice 34: battlefield Elf-count any-color tap mana (slice-9 sibling); "
            "Staff/Mantle rediscovery."
        ),
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Squirrel Nest": RealOracleCurriculum(
        name="Squirrel Nest",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant land\n"
            'Enchanted land has "{T}: Create a 1/1 green Squirrel creature token."'
        ),
        notes=(
            "Slice 35: enchanted-land tap-token grant (Gond sibling); "
            "Earthcraft rediscovery via land host + tap-creature untap."
        ),
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Patrol Signaler": RealOracleCurriculum(
        name="Patrol Signaler",
        types=["Creature", "Kithkin", "Soldier"],
        oracle_text=(
            "{1}{W}, {Q}: Create a 1/1 white Kithkin Soldier creature token. "
            "({Q} is the untap symbol.)"
        ),
        notes=(
            "Slice 36: paid self-{Q} create; Earthcraft + basic Plains double-tap "
            "pays {1}{W} (Spellbook notable)."
        ),
        colors=("W",),
        mana_cost="{1}{W}",
        mana_value=2,
    ),
    "Quillspike": RealOracleCurriculum(
        name="Quillspike",
        types=["Creature", "Beast"],
        oracle_text=(
            "{B/G}, Remove a -1/-1 counter from a creature you control: "
            "This creature gets +3/+3 until end of turn."
        ),
        notes=(
            "Slice 37: hybrid mana + remove-m1m1 cost; +3/+3 until EOT proof-irrelevant; "
            "Devoted Druid rediscovery."
        ),
        colors=("B", "G"),
        mana_cost="{2}{B/G}",
        mana_value=3,
    ),
    "Devoted Druid": RealOracleCurriculum(
        name="Devoted Druid",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "{T}: Add {G}.\n"
            "Put a -1/-1 counter on this creature: Untap this creature."
        ),
        notes="Slice 37 partner: tap mana + m1m1-untap (already COMPLETE).",
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Shalai and Hallar": RealOracleCurriculum(
        name="Shalai and Hallar",
        types=["Legendary", "Creature", "Angel", "Elf"],
        oracle_text=(
            "Flying, vigilance\n"
            "Whenever one or more +1/+1 counters are put on a creature you control, "
            "Shalai and Hallar deals that much damage to target opponent."
        ),
        notes=(
            "Slice 38: COUNTER_ADDED on controlled creature → that-much damage; "
            "Heliod rediscovery (paid lifelink grant). Archangel mass-puts unlock "
            "COMPLETE for frontier but do not close a short explorer loop."
        ),
        colors=("R", "G", "W"),
        mana_cost="{1}{R}{G}{W}",
        mana_value=4,
    ),
    "The Unbeatable Squirrel Girl": RealOracleCurriculum(
        name="The Unbeatable Squirrel Girl",
        types=["Legendary", "Creature", "Squirrel", "Human", "Hero"],
        oracle_text=(
            "Do You Like Squirrels? — Whenever The Unbeatable Squirrel Girl enters "
            "or attacks, create a 1/1 green Squirrel creature token.\n"
            "I LOVE Squirrels! — {1}{G}{G}{G}: Create X 1/1 green Squirrel creature "
            "tokens, where X is the number of Squirrels you control."
        ),
        notes=(
            "Slice 39: ETB create (attacks not modeled) + mana create X=Squirrels; "
            "Altar / Earthcraft rediscovery."
        ),
        colors=("G",),
        mana_cost="{1}{G}{G}{G}",
        mana_value=4,
    ),
    "Shard of the Nightbringer": RealOracleCurriculum(
        name="Shard of the Nightbringer",
        types=["Creature", "C'tan"],
        oracle_text=(
            "Flying\n"
            "Drain Life — When this creature enters, if you cast it, target opponent "
            "loses half their life, rounded up. You gain life equal to the life lost "
            "this way."
        ),
        notes=(
            "Slice 40: ETB intervening-if cast + half-life drain; Vito/Bond COMPLETE "
            "unlock (two-card rediscovery needs bounce/recast — deferred)."
        ),
        colors=("B",),
        mana_cost="{5}{B}{B}{B}",
        mana_value=8,
    ),
    "Tidespout Tyrant": RealOracleCurriculum(
        name="Tidespout Tyrant",
        types=["Creature", "Djinn"],
        oracle_text=(
            "Flying\n"
            "Whenever you cast a spell, return target permanent to its owner's hand."
        ),
        notes=(
            "Slice 41: TriggerEvent.CAST bounce; Sol Ring rediscovery "
            "(artifact cast_from_hand)."
        ),
        colors=("U",),
        mana_cost="{5}{U}{U}{U}",
        mana_value=8,
    ),
    "Sol Ring": RealOracleCurriculum(
        name="Sol Ring",
        types=["Artifact"],
        oracle_text="{T}: Add {C}{C}.",
        notes="Slice 41 partner: {1} rock; cast→tap→Tidespout bounce→recast.",
        mana_cost="{1}",
        mana_value=1,
    ),
    # M5 E01 — gated / restricted tap-mana cluster
    "Metalworker": RealOracleCurriculum(
        name="Metalworker",
        types=["Artifact", "Creature", "Construct"],
        oracle_text=(
            "{T}: Reveal any number of artifact cards in your hand. "
            "Add {C}{C} for each card revealed this way."
        ),
        notes="E01: hand-artifact mana scale; Staff rediscovery with hand seeds.",
        mana_cost="{3}",
        mana_value=3,
    ),
    "Omen Hawker": RealOracleCurriculum(
        name="Omen Hawker",
        types=["Creature", "Cephalid", "Advisor"],
        oracle_text=(
            "{T}: Add {C}{U}. Spend this mana only to activate abilities."
        ),
        notes="E01: spend-only activate-abilities mana; Freed/Pemmin partner.",
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Mox Opal": RealOracleCurriculum(
        name="Mox Opal",
        types=["Artifact"],
        oracle_text=(
            "Metalcraft — {T}: Add one mana of any color. "
            "Activate only if you control three or more artifacts."
        ),
        notes="E01: metalcraft activation gate.",
        mana_cost="{0}",
        mana_value=0,
    ),
    "Fanatic of Rhonas": RealOracleCurriculum(
        name="Fanatic of Rhonas",
        types=["Creature", "Snake", "Druid"],
        oracle_text=(
            "{T}: Add {G}.\n"
            "Ferocious — {T}: Add {G}{G}{G}{G}. "
            "Activate only if you control a creature with power 4 or greater.\n"
            "Eternalize {2}{G}{G} "
            "(Exile this card from your graveyard: Create a token that's a copy of it, "
            "except it's a 4/4 black Zombie Snake Druid with no mana cost. "
            "Eternalize only as a sorcery.)"
        ),
        notes="E01: ferocious gate + basic tap; eternalize proof-irrelevant.",
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Supportive Parents": RealOracleCurriculum(
        name="Supportive Parents",
        types=["Creature", "Human", "Citizen"],
        oracle_text=(
            "Tap two untapped creatures you control: Add one mana of any color."
        ),
        notes="E01: TapCreatureCost quantity=2 mana ability.",
        colors=("G",),
        mana_cost="{2}{G}",
        mana_value=3,
    ),
    # M5 E02 — damage-dealt reflect
    "Spitemare": RealOracleCurriculum(
        name="Spitemare",
        types=["Creature", "Elemental"],
        oracle_text=(
            "Whenever Spitemare is dealt damage, it deals that much damage to any target."
        ),
        notes="E02: DEALT_DAMAGE reflect to any target.",
        colors=("R", "W"),
        mana_cost="{2}{R/W}{R/W}",
        mana_value=4,
    ),
    "Boros Reckoner": RealOracleCurriculum(
        name="Boros Reckoner",
        types=["Creature", "Minotaur", "Wizard"],
        oracle_text=(
            "First strike\n"
            "Whenever Boros Reckoner is dealt damage, it deals that much damage to any target."
        ),
        notes="E02: reflect; first strike proof-irrelevant.",
        colors=("R", "W"),
        mana_cost="{1}{R/W}{R/W}{R/W}",
        mana_value=4,
    ),
    "Coalhauler Swine": RealOracleCurriculum(
        name="Coalhauler Swine",
        types=["Creature", "Boar"],
        oracle_text=(
            "Whenever Coalhauler Swine is dealt damage, it deals that much damage to each player."
        ),
        notes="E02: reflect to each player.",
        colors=("R",),
        mana_cost="{4}{R}{R}",
        mana_value=6,
    ),
    "Brash Taunter": RealOracleCurriculum(
        name="Brash Taunter",
        types=["Creature", "Goblin"],
        oracle_text=(
            "Indestructible\n"
            "Whenever Brash Taunter is dealt damage, it deals that much damage to target opponent."
        ),
        notes="E02: reflect to opponent (fight arm deferred).",
        colors=("R",),
        mana_cost="{4}{R}",
        mana_value=5,
    ),
    "Metropolis Reformer": RealOracleCurriculum(
        name="Metropolis Reformer",
        types=["Creature", "Angel", "Cleric"],
        oracle_text=(
            "Flying, vigilance\n"
            "You have hexproof.\n"
            "Whenever Metropolis Reformer is dealt damage, you gain that much life."
        ),
        notes="E02 reflect + E65 hexproof PI.",
        colors=("W",),
        mana_cost="{2}{W}",
        mana_value=3,
    ),
    # M5 E03 — token create ×2
    "Parallel Lives": RealOracleCurriculum(
        name="Parallel Lives",
        types=["Enchantment"],
        oracle_text=(
            "If an effect would create one or more tokens under your control, "
            "it creates twice that many of those tokens instead."
        ),
        notes="E03: ReplacementDoubleTokens.",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Anointed Procession": RealOracleCurriculum(
        name="Anointed Procession",
        types=["Enchantment"],
        oracle_text=(
            "If an effect would create one or more tokens under your control, "
            "it creates twice that many of those tokens instead."
        ),
        notes="E03: ReplacementDoubleTokens (same text as Parallel Lives).",
        colors=("W",),
        mana_cost="{3}{W}",
        mana_value=4,
    ),
    # M5 E04 — draw triggers
    "Niv-Mizzet, the Firemind": RealOracleCurriculum(
        name="Niv-Mizzet, the Firemind",
        types=["Creature", "Dragon", "Wizard"],
        oracle_text=(
            "Flying\n"
            "Whenever you draw a card, Niv-Mizzet deals 1 damage to any target."
        ),
        notes="E04: DRAW → damage.",
        colors=("U", "R"),
        mana_cost="{2}{U}{U}{R}{R}",
        mana_value=6,
    ),
    "Psychosis Crawler": RealOracleCurriculum(
        name="Psychosis Crawler",
        types=["Artifact", "Creature", "Phyrexian", "Horror"],
        oracle_text="Whenever you draw a card, each opponent loses 1 life.",
        notes="E04: DRAW → lose life (P/T-set clause deferred).",
        mana_cost="{5}",
        mana_value=5,
    ),
    "Horizon Chimera": RealOracleCurriculum(
        name="Horizon Chimera",
        types=["Creature", "Chimera"],
        oracle_text=(
            "Flash\n"
            "Flying, trample\n"
            "Whenever you draw a card, you gain 1 life."
        ),
        notes="E04: DRAW → gain life.",
        colors=("G", "U"),
        mana_cost="{2}{G}{U}",
        mana_value=4,
    ),
    "Queza, Augur of Agonies": RealOracleCurriculum(
        name="Queza, Augur of Agonies",
        types=["Creature", "Cephalid", "Cleric"],
        oracle_text=(
            "Whenever you draw a card, target opponent loses 1 life and you gain 1 life."
        ),
        notes="E04: DRAW → drain.",
        colors=("W", "U", "B"),
        mana_cost="{1}{W}{U}{B}",
        mana_value=4,
    ),
    "Psychic Corrosion": RealOracleCurriculum(
        name="Psychic Corrosion",
        types=["Enchantment"],
        oracle_text="Whenever you draw a card, each opponent mills two cards.",
        notes="E04: DRAW → mill.",
        colors=("U",),
        mana_cost="{2}{U}",
        mana_value=3,
    ),
    # M5 E05 — Curiosity auras
    "Curiosity": RealOracleCurriculum(
        name="Curiosity",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            "Whenever enchanted creature deals damage to an opponent, you may draw a card."
        ),
        notes="E05: DAMAGE_OPPONENT → may draw.",
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Keen Sense": RealOracleCurriculum(
        name="Keen Sense",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            "Whenever enchanted creature deals damage to an opponent, you may draw a card."
        ),
        notes="E05: Curiosity reprint text.",
        colors=("G",),
        mana_cost="{G}",
        mana_value=1,
    ),
    "Ophidian Eye": RealOracleCurriculum(
        name="Ophidian Eye",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            "Whenever enchanted creature deals damage to an opponent, you may draw a card."
        ),
        notes="E05: Curiosity reprint text.",
        colors=("U",),
        mana_cost="{2}{U}",
        mana_value=3,
    ),
    # M5 E06 — grant activated
    "Cryptolith Rite": RealOracleCurriculum(
        name="Cryptolith Rite",
        types=["Enchantment"],
        oracle_text='Creatures you control have "{T}: Add one mana of any color."',
        notes="E06: GrantActivatedAbility tap-any-mana.",
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Basal Sliver": RealOracleCurriculum(
        name="Basal Sliver",
        types=["Creature", "Sliver"],
        oracle_text='All Slivers have "Sacrifice this permanent: Add {B}{B}."',
        notes="E06: grant sac-for-mana to Slivers.",
        colors=("B",),
        mana_cost="{2}{B}",
        mana_value=3,
    ),
    "Resplendent Mentor": RealOracleCurriculum(
        name="Resplendent Mentor",
        types=["Creature", "Human", "Cleric"],
        oracle_text='White creatures you control have "{T}: You gain 1 life."',
        notes="E06: grant tap-gain-life to white creatures.",
        colors=("W",),
        mana_cost="{2}{W}",
        mana_value=3,
    ),
    # M5 E07 — Krenko-scale
    "Krenko, Mob Boss": RealOracleCurriculum(
        name="Krenko, Mob Boss",
        types=["Creature", "Goblin", "Warrior"],
        oracle_text=(
            "{T}: Create X 1/1 red Goblin creature tokens, "
            "where X is the number of Goblins you control."
        ),
        notes="E07: tap create X = controlled Goblins.",
        colors=("R",),
        mana_cost="{2}{R}{R}",
        mana_value=4,
    ),
    # M5 E08 — half-library mill
    "Traumatize": RealOracleCurriculum(
        name="Traumatize",
        types=["Sorcery"],
        oracle_text="Target player mills half their library, rounded down.",
        notes="E08: half-library mill (modeled as once-per-turn activated for COMPLETE).",
        colors=("U",),
        mana_cost="{3}{U}{U}",
        mana_value=5,
    ),
    "Fleet Swallower": RealOracleCurriculum(
        name="Fleet Swallower",
        types=["Creature", "Fish"],
        oracle_text=(
            "Whenever Fleet Swallower attacks, target player mills half their library, "
            "rounded up."
        ),
        notes="E08: ATTACKS → half mill up.",
        colors=("U",),
        mana_cost="{5}{U}{U}",
        mana_value=7,
    ),
    "Terisian Mindbreaker": RealOracleCurriculum(
        name="Terisian Mindbreaker",
        types=["Artifact", "Creature", "Juggernaut"],
        oracle_text=(
            "Whenever Terisian Mindbreaker attacks, defending player mills half their "
            "library, rounded up."
        ),
        notes="E08: ATTACKS → half mill up (unearth deferred).",
        mana_cost="{7}",
        mana_value=7,
    ),
    "Lord Xander, the Collector": RealOracleCurriculum(
        name="Lord Xander, the Collector",
        types=["Creature", "Vampire", "Demon", "Noble"],
        oracle_text=(
            "Whenever Lord Xander attacks, defending player mills half their library, "
            "rounded down."
        ),
        notes="E08: ATTACKS → half mill down (other clauses deferred in curriculum).",
        colors=("U", "B", "R"),
        mana_cost="{4}{U}{B}{R}",
        mana_value=7,
    ),
    # M5 E09 — Aetherflux cast-life + pay-life (sole-gap singleton family)
    "Aetherflux Reservoir": RealOracleCurriculum(
        name="Aetherflux Reservoir",
        types=["Artifact"],
        oracle_text=(
            "Whenever you cast a spell, you gain 1 life for each spell you've cast this turn.\n"
            "Pay 50 life: This Artifact deals 50 damage to any target."
        ),
        notes="E09: sole Spellbook sole-gap; cast-count life + PayLifeCost damage.",
        mana_cost="{4}",
        mana_value=4,
    ),
    # M5 E10 — multi / targeted land untap
    "Palinchron": RealOracleCurriculum(
        name="Palinchron",
        types=["Creature", "Illusion"],
        oracle_text=(
            "Flying\n"
            "When Palinchron enters the battlefield, untap up to seven lands.\n"
            "{2}{U}{U}: Return Palinchron to its owner's hand."
        ),
        notes="E10: ETB untap up to 7 lands + bounce self.",
        colors=("U",),
        mana_cost="{5}{U}{U}",
        mana_value=7,
    ),
    "Peregrine Drake": RealOracleCurriculum(
        name="Peregrine Drake",
        types=["Creature", "Drake"],
        oracle_text="When this creature enters, untap up to five lands.",
        notes="E10: ETB untap up to 5 lands.",
        colors=("U",),
        mana_cost="{4}{U}",
        mana_value=5,
    ),
    "Cloud of Faeries": RealOracleCurriculum(
        name="Cloud of Faeries",
        types=["Creature", "Faerie"],
        oracle_text=(
            "Flying\n"
            "When this creature enters, untap up to two lands.\n"
            "Cycling {2} ({2}, Discard this card: Draw a card.)"
        ),
        notes="E10: ETB untap up to 2; cycling proof-irrelevant.",
        colors=("U",),
        mana_cost="{1}{U}",
        mana_value=2,
    ),
    "Argothian Elder": RealOracleCurriculum(
        name="Argothian Elder",
        types=["Creature", "Elf", "Druid"],
        oracle_text="{T}: Untap two target lands.",
        notes="E10: tap untap two lands.",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Ley Weaver": RealOracleCurriculum(
        name="Ley Weaver",
        types=["Creature", "Human", "Druid"],
        oracle_text="{T}: Untap two target lands.",
        notes="E10: tap untap two lands (Partner ignored in curriculum).",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    # M5 E11 — scaled mana remainders
    "Magus of the Coffers": RealOracleCurriculum(
        name="Magus of the Coffers",
        types=["Creature", "Human", "Wizard"],
        oracle_text="{2}, {T}: Add {B} for each Swamp you control.",
        notes="E11: swamp-count mana.",
        colors=("B",),
        mana_cost="{3}{B}",
        mana_value=4,
    ),
    "Bighorner Rancher": RealOracleCurriculum(
        name="Bighorner Rancher",
        types=["Creature", "Human", "Ranger"],
        oracle_text=(
            "{T}: Add an amount of {G} equal to the greatest power among creatures you control."
        ),
        notes="E11: greatest-power green mana.",
        colors=("G",),
        mana_cost="{4}{G}",
        mana_value=5,
    ),
    "Arbor Adherent": RealOracleCurriculum(
        name="Arbor Adherent",
        types=["Creature", "Human", "Druid"],
        oracle_text=(
            "{T}: Add X mana of any one color, where X is the greatest toughness among "
            "other creatures you control."
        ),
        notes="E11: greatest toughness among others → any color.",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Kydele, Chosen of Kruphix": RealOracleCurriculum(
        name="Kydele, Chosen of Kruphix",
        types=["Creature", "Human", "Wizard"],
        oracle_text=(
            "{T}: Add {C} for each card you've drawn this turn.\n"
            "Partner (You can have two commanders if both have partner.)"
        ),
        notes="E11: cards-drawn mana; Partner irrelevant.",
        colors=("G", "U"),
        mana_cost="{2}{G}{U}",
        mana_value=4,
    ),
    "Alena, Kessig Trapper": RealOracleCurriculum(
        name="Alena, Kessig Trapper",
        types=["Creature", "Human", "Ranger"],
        oracle_text=(
            "{T}: Add an amount of {R} equal to the greatest power among creatures you "
            "control that entered this turn.\n"
            "Partner (You can have two commanders if both have partner.)"
        ),
        notes="E11: entered-this-turn greatest power → red.",
        colors=("R",),
        mana_cost="{4}{R}",
        mana_value=5,
    ),
    "Selvala, Heart of the Wilds": RealOracleCurriculum(
        name="Selvala, Heart of the Wilds",
        types=["Creature", "Elf", "Scout"],
        oracle_text=(
            "{G}, {T}: Add X mana in any combination of colors, where X is the greatest "
            "power among creatures you control."
        ),
        notes="E11: Selvala greatest-power any-color (modeled as any_color pool).",
        colors=("G",),
        mana_cost="{1}{G}{G}",
        mana_value=3,
    ),
    # M5 E12 — cast-trigger effect family
    "Birgi, God of Storytelling": RealOracleCurriculum(
        name="Birgi, God of Storytelling",
        types=["Legendary", "Creature", "God"],
        oracle_text=(
            "Whenever you cast a spell, add {R}.\n"
            "Until end of turn, you don't lose this mana as steps and phases end.\n"
            "Creatures you control have haste."
        ),
        notes="E12: cast → {R}; linger/haste proof-irrelevant.",
        colors=("R",),
        mana_cost="{2}{R}",
        mana_value=3,
    ),
    "Forsaken Monument": RealOracleCurriculum(
        name="Forsaken Monument",
        types=["Legendary", "Artifact"],
        oracle_text=(
            "Whenever you cast a colorless spell, you gain 2 life.\n"
            "Colorless creatures you control get +2/+2."
        ),
        notes="E12: cast colorless → life; anthem irrelevant.",
        mana_cost="{5}",
        mana_value=5,
    ),
    "Animar, Soul of Elements": RealOracleCurriculum(
        name="Animar, Soul of Elements",
        types=["Legendary", "Creature", "Elemental"],
        oracle_text=(
            "Whenever you cast a creature spell, put a +1/+1 counter on Animar."
        ),
        notes="E12: cast creature → p1p1 (cost reduction deferred).",
        colors=("G", "U", "R"),
        mana_cost="{U}{R}{G}",
        mana_value=3,
    ),
    "Runaway Steam-Kin": RealOracleCurriculum(
        name="Runaway Steam-Kin",
        types=["Creature", "Elemental"],
        oracle_text=(
            "Whenever you cast a red spell, if this creature has fewer than three +1/+1 "
            "counters on it, put a +1/+1 counter on this creature."
        ),
        notes="E12: cast red → p1p1 capped at 3.",
        colors=("R",),
        mana_cost="{1}{R}",
        mana_value=2,
    ),
    "Vivi Ornitier": RealOracleCurriculum(
        name="Vivi Ornitier",
        types=["Legendary", "Creature", "Wizard"],
        oracle_text=(
            "Whenever you cast a noncreature spell, put a +1/+1 counter on Vivi Ornitier "
            "and it deals 1 damage to each opponent."
        ),
        notes="E12: cast noncreature → p1p1 + damage.",
        colors=("U", "R"),
        mana_cost="{1}{U}{R}",
        mana_value=3,
    ),
    # M5 E13a — self-ETB scaled damage / life / draw
    "Murderous Redcap": RealOracleCurriculum(
        name="Murderous Redcap",
        types=["Creature", "Goblin", "Assassin"],
        oracle_text=(
            "When this creature enters, it deals damage equal to its power to any target.\n"
            "Persist (When this creature dies, if it had no -1/-1 counters on it, return it "
            "to the battlefield under its owner's control with a -1/-1 counter on it.)"
        ),
        notes="E13a: ETB power damage; Persist irrelevant.",
        colors=("B", "R"),
        mana_cost="{2}{B}{R}",
        mana_value=4,
    ),
    "Fanatic of Mogis": RealOracleCurriculum(
        name="Fanatic of Mogis",
        types=["Creature", "Minotaur", "Shaman"],
        oracle_text=(
            "When this creature enters, it deals damage to each opponent equal to your "
            "devotion to red. (Each {R} in the mana costs of permanents you control "
            "counts toward your devotion to red.)"
        ),
        notes="E13a: ETB devotion-red damage.",
        colors=("R",),
        mana_cost="{3}{R}",
        mana_value=4,
    ),
    "Gray Merchant of Asphodel": RealOracleCurriculum(
        name="Gray Merchant of Asphodel",
        types=["Creature", "Zombie"],
        oracle_text=(
            "When this creature enters, each opponent loses X life, where X is your "
            "devotion to black. You gain life equal to the life lost this way."
        ),
        notes="E13a: Gary devotion drain.",
        colors=("B",),
        mana_cost="{3}{B}{B}",
        mana_value=5,
    ),
    "Edgar, King of Figaro": RealOracleCurriculum(
        name="Edgar, King of Figaro",
        types=["Legendary", "Creature", "Human", "Noble"],
        oracle_text="When Edgar enters, draw a card for each artifact you control.",
        notes="E13a: ETB draw = artifacts.",
        colors=("U",),
        mana_cost="{4}{U}",
        mana_value=5,
    ),
    # M5 E14 — dies-trigger payoffs
    "Pitiless Plunderer": RealOracleCurriculum(
        name="Pitiless Plunderer",
        types=["Creature", "Human", "Pirate"],
        oracle_text=(
            "Whenever another creature you control dies, create a Treasure token. "
            '(It\'s an artifact with "{T}, Sacrifice this token: Add one mana of any color.")'
        ),
        notes="E14: dies → Treasure.",
        colors=("B",),
        mana_cost="{3}{B}",
        mana_value=4,
    ),
    "Goblin Sharpshooter": RealOracleCurriculum(
        name="Goblin Sharpshooter",
        types=["Creature", "Goblin"],
        oracle_text="Whenever a creature dies, untap this creature.",
        notes="E14: dies → untap self (tap-damage deferred).",
        colors=("R",),
        mana_cost="{2}{R}",
        mana_value=3,
    ),
    "Teysa, Orzhov Scion": RealOracleCurriculum(
        name="Teysa, Orzhov Scion",
        types=["Legendary", "Creature", "Human", "Advisor"],
        oracle_text=(
            "Whenever another black creature you control dies, create a 1/1 white Spirit "
            "creature token with flying."
        ),
        notes="E14: black dies → Spirit (exile outlet deferred).",
        colors=("W", "B"),
        mana_cost="{1}{W}{B}",
        mana_value=3,
    ),
    "Blood Artist": RealOracleCurriculum(
        name="Blood Artist",
        types=["Creature", "Vampire"],
        oracle_text=(
            "Whenever this creature or another creature dies, target player loses 1 life "
            "and you gain 1 life."
        ),
        notes="E14: dies drain.",
        colors=("B",),
        mana_cost="{1}{B}",
        mana_value=2,
    ),
    "Pawn of Ulamog": RealOracleCurriculum(
        name="Pawn of Ulamog",
        types=["Creature", "Vampire", "Shaman"],
        oracle_text=(
            "Whenever this creature or another nontoken creature you control dies, you may "
            "create a 0/1 colorless Eldrazi Spawn creature token."
        ),
        notes="E14: nontoken dies → Spawn.",
        colors=("B",),
        mana_cost="{1}{B}{B}",
        mana_value=3,
    ),
    # M5 E16 — sac-outlet payoffs
    "Goblin Bombardment": RealOracleCurriculum(
        name="Goblin Bombardment",
        types=["Enchantment"],
        oracle_text="Sacrifice a creature: This enchantment deals 1 damage to any target.",
        notes="E16: sac → 1 damage.",
        colors=("R",),
        mana_cost="{1}{R}",
        mana_value=2,
    ),
    "Blasting Station": RealOracleCurriculum(
        name="Blasting Station",
        types=["Artifact"],
        oracle_text=(
            "{T}, Sacrifice a creature: This artifact deals 1 damage to any target.\n"
            "Whenever a creature enters, you may untap this artifact."
        ),
        notes="E16 sac damage + E13b ETB untap self.",
        mana_cost="{3}",
        mana_value=3,
    ),
    "Altar of Dementia": RealOracleCurriculum(
        name="Altar of Dementia",
        types=["Artifact"],
        oracle_text=(
            "Sacrifice a creature: Target player mills cards equal to the sacrificed "
            "creature's power."
        ),
        notes="E16: sac → mill = power.",
        mana_cost="{2}",
        mana_value=2,
    ),
    "Composite Golem": RealOracleCurriculum(
        name="Composite Golem",
        types=["Artifact", "Creature", "Golem"],
        oracle_text="Sacrifice this creature: Add {W}{U}{B}{R}{G}.",
        notes="E16: sac-self → rainbow mana.",
        mana_cost="{6}",
        mana_value=6,
    ),
    "Ayara, First of Locthwain": RealOracleCurriculum(
        name="Ayara, First of Locthwain",
        types=["Legendary", "Creature", "Elf", "Noble"],
        oracle_text="{T}, Sacrifice another black creature: Draw a card.",
        notes="E16: tap+sac → draw (black filter soft).",
        colors=("B",),
        mana_cost="{B}{B}{B}",
        mana_value=3,
    ),
# M5 E18 — GY → hand recursion
    "Eternal Witness": RealOracleCurriculum(
        name="Eternal Witness",
        types=["Creature", "Human", "Shaman"],
        oracle_text=(
            "When this creature enters, you may return target card from your graveyard "
            "to your hand."
        ),
        notes="E18: ETB GY→hand.",
        colors=("G",),
        mana_cost="{1}{G}{G}",
        mana_value=3,
    ),
    "Archaeomancer": RealOracleCurriculum(
        name="Archaeomancer",
        types=["Creature", "Human", "Wizard"],
        oracle_text=(
            "When this creature enters, return target instant or sorcery card from your "
            "graveyard to your hand."
        ),
        notes="E18: ETB instant/sorcery GY→hand.",
        colors=("U",),
        mana_cost="{2}{U}{U}",
        mana_value=4,
    ),
    "Auriok Salvagers": RealOracleCurriculum(
        name="Auriok Salvagers",
        types=["Creature", "Human", "Soldier"],
        oracle_text=(
            "{1}{W}: Return target artifact card with mana value 1 or less from your "
            "graveyard to your hand."
        ),
        notes="E18: Salvagers loop piece.",
        colors=("W",),
        mana_cost="{3}{W}",
        mana_value=4,
    ),
    "Enduring Renewal": RealOracleCurriculum(
        name="Enduring Renewal",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature is put into your graveyard from the battlefield, "
            "return it to your hand."
        ),
        notes="E18: dies → hand (Renewal).",
        colors=("W",),
        mana_cost="{2}{W}{W}",
        mana_value=4,
    ),
    "Doubling Season": RealOracleCurriculum(
        name="Doubling Season",
        types=["Enchantment"],
        oracle_text=(
            "If an effect would create one or more tokens under your control, "
            "it creates twice that many of those tokens instead.\n"
            "If an effect would put one or more counters on a permanent you control, "
            "it puts twice that many of those counters on that permanent instead."
        ),
        notes="E20: token + counter doubling.",
        colors=("G",),
        mana_cost="{4}{G}",
        mana_value=5,
    ),
    "Primal Vigor": RealOracleCurriculum(
        name="Primal Vigor",
        types=["Enchantment"],
        oracle_text=(
            "If one or more tokens would be created, "
            "twice that many of those tokens are created instead.\n"
            "If one or more +1/+1 counters would be put on a creature, "
            "twice that many +1/+1 counters are put on that creature instead."
        ),
        notes="E20: Primal Vigor token + p1p1 double.",
        colors=("G",),
        mana_cost="{4}{G}",
        mana_value=5,
    ),
    "Viral Drake": RealOracleCurriculum(
        name="Viral Drake",
        types=["Creature", "Phyrexian", "Drake"],
        oracle_text=(
            "Flying\n"
            "Infect (This creature deals damage to creatures in the form of -1/-1 "
            "counters and to players in the form of poison counters.)\n"
            "{3}{U}: Proliferate. (Choose any number of permanents and/or players, "
            "then give each another counter of each kind already there.)"
        ),
        notes="E21: proliferate; infect is proof-irrelevant.",
        colors=("U",),
        mana_cost="{2}{U}",
        mana_value=3,
    ),
    "Quirion Ranger": RealOracleCurriculum(
        name="Quirion Ranger",
        types=["Creature", "Elf", "Ranger"],
        oracle_text=(
            "Return a Forest you control to its owner's hand: Untap target creature. "
            "Activate only once each turn."
        ),
        notes="E19: bounce Forest cost → untap.",
        colors=("G",),
        mana_cost="{G}",
        mana_value=1,
    ),
    "Wirewood Symbiote": RealOracleCurriculum(
        name="Wirewood Symbiote",
        types=["Creature", "Insect"],
        oracle_text=(
            "Return an Elf you control to its owner's hand: Untap target creature. "
            "Activate only once each turn."
        ),
        notes="E19: bounce Elf cost → untap.",
        colors=("G",),
        mana_cost="{G}",
        mana_value=1,
    ),
    "Meloku the Clouded Mirror": RealOracleCurriculum(
        name="Meloku the Clouded Mirror",
        types=["Legendary", "Creature", "Moonfolk", "Wizard"],
        oracle_text=(
            "Flying\n"
            "{1}, Return a land you control to its owner's hand: "
            "Create a 1/1 blue Illusion creature token with flying."
        ),
        notes="E19: bounce land cost → Illusion token.",
        colors=("U",),
        mana_cost="{4}{U}",
        mana_value=5,
    ),
    "Chulane, Teller of Tales": RealOracleCurriculum(
        name="Chulane, Teller of Tales",
        types=["Legendary", "Creature", "Human", "Druid"],
        oracle_text=(
            "Vigilance\n"
            "{3}, {T}: Return target creature you control to its owner's hand."
        ),
        notes=(
            "E19: activated bounce only (cast→draw/land put deferred)."
        ),
        colors=("G", "W", "U"),
        mana_cost="{2}{G}{W}{U}",
        mana_value=5,
    ),
    "Brood Monitor": RealOracleCurriculum(
        name="Brood Monitor",
        types=["Creature", "Eldrazi", "Drone"],
        oracle_text=(
            "Devoid (This card has no color.)\n"
            "When this creature enters, create three 1/1 colorless Eldrazi Scion "
            'creature tokens. They have "Sacrifice this token: Add {C}."'
        ),
        notes="E22a: ETB Eldrazi Scions.",
        colors=(),
        mana_cost="{4}{G}{G}",
        mana_value=6,
    ),
    "Emrakul's Hatcher": RealOracleCurriculum(
        name="Emrakul's Hatcher",
        types=["Creature", "Eldrazi", "Drone"],
        oracle_text=(
            "When this creature enters, create three 0/1 colorless Eldrazi Spawn "
            'creature tokens. They have "Sacrifice this token: Add {C}."'
        ),
        notes="E22a: ETB Eldrazi Spawn.",
        colors=("R",),
        mana_cost="{4}{R}",
        mana_value=5,
    ),
    "Spawnsire of Ulamog": RealOracleCurriculum(
        name="Spawnsire of Ulamog",
        types=["Creature", "Eldrazi"],
        oracle_text=(
            "Annihilator 1 (Whenever this creature attacks, defending player "
            "sacrifices a permanent of their choice.)\n"
            '{4}: Create two 0/1 colorless Eldrazi Spawn creature tokens. They have '
            '"Sacrifice this token: Add {C}."'
        ),
        notes="E22a: activated Eldrazi Spawn (outside-game clause omitted).",
        colors=(),
        mana_cost="{10}",
        mana_value=10,
    ),
    "Exalted Sunborn": RealOracleCurriculum(
        name="Exalted Sunborn",
        types=["Creature", "Angel", "Wizard"],
        oracle_text=(
            "Flying, lifelink\n"
            "If one or more tokens would be created under your control, "
            "twice that many of those tokens are created instead.\n"
            "Warp {1}{W} (You may cast this card from your hand for its warp cost. "
            "Exile this creature at the beginning of the next end step, then you may "
            "cast it from exile on a later turn.)"
        ),
        notes="E22a: double-tokens sibling (Exalted wording).",
        colors=("W",),
        mana_cost="{3}{W}{W}",
        mana_value=5,
    ),
    "Ajani's Chosen": RealOracleCurriculum(
        name="Ajani's Chosen",
        types=["Creature", "Cat", "Soldier"],
        oracle_text=(
            "Whenever an enchantment you control enters, create a 2/2 white Cat "
            "creature token. If that enchantment is an Aura, you may attach it to the token."
        ),
        notes="E22a: enchantment ETB → Cat (Aura attach ignored).",
        colors=("W",),
        mana_cost="{2}{W}{W}",
        mana_value=4,
    ),
    "Arcanis the Omnipotent": RealOracleCurriculum(
        name="Arcanis the Omnipotent",
        types=["Legendary", "Creature", "Wizard"],
        oracle_text="{T}: Draw three cards.",
        notes="E60: tap-draw N.",
        colors=("U",),
        mana_cost="{3}{U}{U}{U}",
        mana_value=6,
    ),
    "Azami, Lady of Scrolls": RealOracleCurriculum(
        name="Azami, Lady of Scrolls",
        types=["Legendary", "Creature", "Human", "Wizard"],
        oracle_text="Tap an untapped Wizard you control: Draw a card.",
        notes="E60: tap Wizard subtype → draw.",
        colors=("U",),
        mana_cost="{2}{U}{U}{U}",
        mana_value=5,
    ),
    "Temple Bell": RealOracleCurriculum(
        name="Temple Bell",
        types=["Artifact"],
        oracle_text="{T}: Each player draws a card.",
        notes="E60: each-player draw modeled as you draw 1.",
        colors=(),
        mana_cost="{3}",
        mana_value=3,
    ),
    "Kwain, Itinerant Meddler": RealOracleCurriculum(
        name="Kwain, Itinerant Meddler",
        types=["Legendary", "Creature", "Rabbit", "Wizard"],
        oracle_text=(
            "{T}: Each player may draw a card, then each player who drew a card "
            "this way gains 1 life."
        ),
        notes="E60: optional each-draw → you draw 1 (life rider ignored).",
        colors=("W", "U"),
        mana_cost="{W}{U}",
        mana_value=2,
    ),

    "Lightning Greaves": RealOracleCurriculum(
        name="Lightning Greaves",
        types=["Artifact", "Equipment"],
        oracle_text=(
            "Equipped creature has haste and shroud. "
            "(It can't be the target of spells or abilities.)\n"
            "Equip {0}"
        ),
        notes="E65: equipped shroud PI.",
        mana_cost="{2}",
        mana_value=2,
    ),
    "Darksteel Plate": RealOracleCurriculum(
        name="Darksteel Plate",
        types=["Artifact", "Equipment"],
        oracle_text=(
            "Indestructible\n"
            "Equipped creature has indestructible.\n"
            "Equip {2}"
        ),
        notes="E57: equipment indestructible PI.",
        mana_cost="{3}",
        mana_value=3,
    ),
    "Anara, Wolvid Familiar": RealOracleCurriculum(
        name="Anara, Wolvid Familiar",
        types=["Legendary", "Creature", "Wolf", "Beast"],
        oracle_text=(
            "During your turn, commanders you control have indestructible. "
            '(Effects that say "destroy" don\'t destroy them. A creature with '
            "indestructible can't be destroyed by damage.)\n"
            "Partner (You can have two commanders if both have partner.)"
        ),
        notes="E57: commander indestructible PI.",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Avacyn, Angel of Hope": RealOracleCurriculum(
        name="Avacyn, Angel of Hope",
        types=["Legendary", "Creature", "Angel"],
        oracle_text=(
            "Flying, vigilance, indestructible\n"
            "Other permanents you control have indestructible."
        ),
        notes="E57: mass indestructible PI.",
        colors=("W",),
        mana_cost="{5}{W}{W}{W}",
        mana_value=8,
    ),
    "Myr Matrix": RealOracleCurriculum(
        name="Myr Matrix",
        types=["Artifact"],
        oracle_text=(
            'Indestructible (Effects that say "destroy" don\'t destroy this artifact.)\n'
            "Myr creatures get +1/+1.\n"
            "{5}: Create a 1/1 colorless Myr artifact creature token."
        ),
        notes="E57: Myr Matrix indestructible + token create.",
        mana_cost="{5}",
        mana_value=5,
    ),

    "Old Gnawbone": RealOracleCurriculum(
        name="Old Gnawbone",
        types=["Legendary", "Creature", "Dragon"],
        oracle_text=(
            "Flying\n"
            "Whenever a creature you control deals combat damage to a player, "
            "create that many Treasure tokens."
        ),
        notes="E22b: combat damage → that many Treasures.",
        colors=("G",),
        mana_cost="{5}{G}{G}",
        mana_value=7,
    ),
    "Grim Hireling": RealOracleCurriculum(
        name="Grim Hireling",
        types=["Creature", "Tiefling", "Rogue"],
        oracle_text=(
            "Whenever one or more creatures you control deal combat damage to a player, "
            "create two Treasure tokens."
        ),
        notes="E22b: combat damage → two Treasures.",
        colors=("B",),
        mana_cost="{3}{B}",
        mana_value=4,
    ),
    "Smaug the Impenetrable": RealOracleCurriculum(
        name="Smaug the Impenetrable",
        types=["Legendary", "Creature", "Dragon"],
        oracle_text=(
            "Flying\n"
            "Whenever Smaug is dealt noncombat damage, create that many Treasure tokens."
        ),
        notes="E22b: dealt damage → Treasures (noncombat gate not modeled).",
        colors=("R",),
        mana_cost="{5}{R}",
        mana_value=6,
    ),

    "All Will Be One": RealOracleCurriculum(
        name="All Will Be One",
        types=["Enchantment"],
        oracle_text=(
            "Whenever you put one or more counters on a permanent or player, "
            "this enchantment deals that much damage to target opponent, "
            "creature an opponent controls, or planeswalker an opponent controls."
        ),
        notes="E52: COUNTER_ADDED → that much damage.",
        colors=("R",),
        mana_cost="{5}{R}{R}",
        mana_value=7,
    ),
    "Flourishing Defenses": RealOracleCurriculum(
        name="Flourishing Defenses",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a -1/-1 counter is put on a creature, "
            "you may create a 1/1 green Elf Warrior creature token."
        ),
        notes="E52: m1m1 put → Elf Warrior token.",
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),

    "Filigree Sages": RealOracleCurriculum(
        name="Filigree Sages",
        types=["Artifact", "Creature", "Vedalken", "Artificer"],
        oracle_text="{2}{U}: Untap target artifact.",
        notes="E67a: untap target artifact.",
        colors=("U",),
        mana_cost="{3}{U}",
        mana_value=4,
    ),
    "Corridor Monitor": RealOracleCurriculum(
        name="Corridor Monitor",
        types=["Artifact", "Creature", "Construct"],
        oracle_text=(
            "When this creature enters, untap target artifact or creature you control."
        ),
        notes="E67a: ETB untap artifact/creature.",
        colors=("U",),
        mana_cost="{1}{U}",
        mana_value=2,
    ),
    "Clock of Omens": RealOracleCurriculum(
        name="Clock of Omens",
        types=["Artifact"],
        oracle_text="Tap two untapped artifacts you control: Untap target artifact.",
        notes="E67a: tap two artifacts → untap artifact.",
        mana_cost="{4}",
        mana_value=4,
    ),

    "Hyrax Tower Scout": RealOracleCurriculum(
        name="Hyrax Tower Scout",
        types=["Creature", "Human", "Scout"],
        oracle_text="When this creature enters, untap target creature.",
        notes="E13b: self-ETB untap target creature.",
        colors=("G",),
        mana_cost="{2}{G}",
        mana_value=3,
    ),
    "Warstorm Surge": RealOracleCurriculum(
        name="Warstorm Surge",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature you control enters, "
            "it deals damage equal to its power to any target."
        ),
        notes="E13b: controlled creature ETB → subject power damage.",
        colors=("R",),
        mana_cost="{3}{R}",
        mana_value=4,
    ),
    "Sporemound": RealOracleCurriculum(
        name="Sporemound",
        types=["Creature", "Fungus"],
        oracle_text=(
            "Landfall — Whenever a land you control enters, "
            "create a 1/1 green Saproling creature token."
        ),
        notes="E13b: landfall create Saproling.",
        colors=("G",),
        mana_cost="{3}{G}",
        mana_value=4,
    ),
    "Molten Gatekeeper": RealOracleCurriculum(
        name="Molten Gatekeeper",
        types=["Artifact", "Creature", "Golem"],
        oracle_text=(
            "Whenever another creature you control enters, "
            "this creature deals 1 damage to each opponent.\n"
            "Unearth {R} ({R}: Return this card from your graveyard to the "
            "battlefield. It gains haste. Exile it at the beginning of the next "
            "end step or if it would leave the battlefield. Unearth only as a sorcery.)"
        ),
        notes="E13b: ETB damage; unearth proof-irrelevant.",
        colors=("R",),
        mana_cost="{2}",
        mana_value=2,
    ),
    "Yotian Dissident": RealOracleCurriculum(
        name="Yotian Dissident",
        types=["Creature", "Human", "Artificer"],
        oracle_text=(
            "Whenever an artifact you control enters, "
            "put a +1/+1 counter on target creature you control."
        ),
        notes="E13b: artifact ETB → p1p1 target.",
        colors=("G", "W"),
        mana_cost="{G}{W}",
        mana_value=2,
    ),

    "Bloodletter of Aclazotz": RealOracleCurriculum(
        name="Bloodletter of Aclazotz",
        types=["Creature", "Vampire", "Demon"],
        oracle_text=(
            "Flying\n"
            "If an opponent would lose life during your turn, "
            "they lose twice that much life instead. "
            "(Damage causes loss of life.)"
        ),
        notes="E50: double opponent life loss; Flying PI.",
        colors=("B",),
        mana_cost="{1}{B}{B}{B}",
        mana_value=4,
    ),
    "Alhammarret's Archive": RealOracleCurriculum(
        name="Alhammarret's Archive",
        types=["Legendary", "Artifact"],
        oracle_text=(
            "If you would gain life, you gain twice that much life instead.\n"
            "If you would draw a card except the first one you draw in each of "
            "your draw steps, draw two cards instead."
        ),
        notes="E50: double life gain + double draw.",
        mana_cost="{5}",
        mana_value=5,
    ),
    "Everlasting Torment": RealOracleCurriculum(
        name="Everlasting Torment",
        types=["Enchantment"],
        oracle_text=(
            "Players can't gain life.\n"
            "Damage can't be prevented.\n"
            "All damage is dealt as though its source had wither. "
            "(A source with wither deals damage to creatures in the form of "
            "-1/-1 counters.)"
        ),
        notes="E50: can't-gain; prevent/wither PI.",
        colors=("B", "R"),
        mana_cost="{2}{B/R}",
        mana_value=3,
    ),

    "Mind Over Matter": RealOracleCurriculum(
        name="Mind Over Matter",
        types=["Enchantment"],
        oracle_text=(
            "Discard a card: You may tap or untap target artifact, creature, or land."
        ),
        notes="E62: DiscardCost → untap target.",
        colors=("U",),
        mana_cost="{2}{U}{U}{U}{U}",
        mana_value=6,
    ),
    "Skirge Familiar": RealOracleCurriculum(
        name="Skirge Familiar",
        types=["Creature", "Phyrexian", "Imp"],
        oracle_text="Flying\nDiscard a card: Add {B}.",
        notes="E62: DiscardCost → {B}; Flying PI.",
        colors=("B",),
        mana_cost="{4}{B}",
        mana_value=5,
    ),
    "Glint-Horn Buccaneer": RealOracleCurriculum(
        name="Glint-Horn Buccaneer",
        types=["Creature", "Minotaur", "Pirate"],
        oracle_text=(
            "Haste\n"
            "Whenever you discard a card, this creature deals 1 damage to each opponent.\n"
            "{1}{R}, Discard a card: Draw a card. Activate only if this creature is attacking."
        ),
        notes="E62: discard → damage; discard+mana → draw.",
        colors=("R",),
        mana_cost="{2}{R}{R}",
        mana_value=4,
    ),

    "Astral Cornucopia": RealOracleCurriculum(
        name="Astral Cornucopia",
        types=["Artifact"],
        oracle_text=(
            "This artifact enters with X charge counters on it.\n"
            "{T}: Choose a color. Add one mana of that color for each charge "
            "counter on this artifact."
        ),
        notes="E61: charge-scaled tap mana; enters-with-X PI (seed counters).",
        mana_cost="{X}{X}{X}",
        mana_value=0,
    ),
    "Druids' Repository": RealOracleCurriculum(
        name="Druids' Repository",
        types=["Enchantment"],
        oracle_text=(
            "Whenever a creature you control attacks, put a charge counter on "
            "this enchantment.\n"
            "Remove a charge counter from this enchantment: Add one mana of any color."
        ),
        notes="E61: attacks → charge; remove charge → any mana.",
        colors=("G",),
        mana_cost="{1}{G}{G}",
        mana_value=3,
    ),
    "Coretapper": RealOracleCurriculum(
        name="Coretapper",
        types=["Artifact", "Creature", "Myr"],
        oracle_text=(
            "{T}: Put a charge counter on target artifact.\n"
            "Sacrifice this creature: Put two charge counters on target artifact."
        ),
        notes="E61: put charge counters on target artifact.",
        mana_cost="{2}",
        mana_value=2,
    ),

    "Bear Umbra": RealOracleCurriculum(
        name="Bear Umbra",
        types=["Enchantment", "Aura"],
        oracle_text=(
            "Enchant creature\n"
            'Enchanted creature gets +2/+2 and has '
            '"Whenever this creature attacks, untap all lands you control."\n'
            "Umbra armor (If enchanted creature would be destroyed, instead "
            "remove all damage from it and destroy this Aura.)"
        ),
        notes="E15a: attacks → untap lands (Curiosity-style controlled_creature approx).",
        colors=("G",),
        mana_cost="{2}{G}{G}",
        mana_value=4,
    ),
    "Caltrops": RealOracleCurriculum(
        name="Caltrops",
        types=["Artifact"],
        oracle_text="Whenever a creature attacks, this artifact deals 1 damage to it.",
        notes="E15a: attacks → damage trigger subject.",
        mana_cost="{3}",
        mana_value=3,
    ),
    "Dream Trawler": RealOracleCurriculum(
        name="Dream Trawler",
        types=["Creature", "Sphinx"],
        oracle_text=(
            "Flying, lifelink\n"
            "Whenever you draw a card, this creature gets +1/+0 until end of turn.\n"
            "Whenever this creature attacks, draw a card.\n"
            "Discard a card: This creature gains hexproof until end of turn. Tap it."
        ),
        notes="E15a: attacks → draw; other clauses PI.",
        colors=("W", "U"),
        mana_cost="{2}{W}{W}{U}{U}",
        mana_value=6,
    ),

    "Basking Broodscale": RealOracleCurriculum(
        name="Basking Broodscale",
        types=["Creature", "Eldrazi", "Lizard"],
        oracle_text=(
            "Devoid (This card has no color.)\n"
            "{1}{G}: Adapt 1. (If this creature has no +1/+1 counters on it, "
            "put a +1/+1 counter on it.)\n"
            "Whenever one or more +1/+1 counters are put on this creature, "
            'you may create a 0/1 colorless Eldrazi Spawn creature token with '
            '"Sacrifice this token: Add {C}."'
        ),
        notes="E53: Adapt + p1p1→Spawn.",
        colors=(),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
    "Benthic Biomancer": RealOracleCurriculum(
        name="Benthic Biomancer",
        types=["Creature", "Merfolk", "Wizard"],
        oracle_text=(
            "{1}{U}: Adapt 1. (If this creature has no +1/+1 counters on it, "
            "put a +1/+1 counter on it.)\n"
            "Whenever one or more +1/+1 counters are put on this creature, "
            "draw a card, then discard a card."
        ),
        notes="E53: Adapt + p1p1→draw (discard omitted combo-favorable).",
        colors=("U",),
        mana_cost="{U}",
        mana_value=1,
    ),
    "Incubation Druid": RealOracleCurriculum(
        name="Incubation Druid",
        types=["Creature", "Elf", "Druid"],
        oracle_text=(
            "{3}{G}{G}: Adapt 3. (If this creature has no +1/+1 counters on it, "
            "put three +1/+1 counters on it.)"
        ),
        notes="E53: Adapt 3 only (land-produce tap deferred).",
        colors=("G",),
        mana_cost="{1}{G}",
        mana_value=2,
    ),
}
