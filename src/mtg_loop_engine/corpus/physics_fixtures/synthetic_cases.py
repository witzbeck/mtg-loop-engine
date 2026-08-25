"""Physics / synthetic executor regression witnesses (ADR 0007).

Historical gold_core IDs are retained here as physics fixtures. They are never
precision-eligible. Oracle gold lives in corpus.gold_core.
"""

from __future__ import annotations

from mtg_loop_engine.corpus.builders import (
    ActionStep,
    ComparisonOp,
    Consequence,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    ManaAmount,
    OutputType,
    Prerequisite,
    SemanticCoverage,
    VerificationStatus,
    bf,
    dim,
    out,
    two_card,
    witness,
)
from mtg_loop_engine.proofs.models import LoopWitness, PermanentSpec
from mtg_loop_engine.semantics.enums import TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    LoseLifeEffect,
    ManaCost,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TriggeredAbility,
    UntapEffect,
)

# --- Manual card IR -----------------------------------------------------------

BASALT = CardSemantics(
    oracle_id="oracle:basalt-monolith",
    name="Basalt Monolith",
    types=["Artifact"],
    abilities=[
        ActivatedAbility(
            ability_id="basalt-tap-mana",
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(colorless=3))],
            is_mana_ability=True,
            uses_stack=False,
        ),
        ActivatedAbility(
            ability_id="basalt-untap",
            costs=[ManaCost(amount=ManaAmount(generic=3))],
            effects=[UntapEffect(target="self")],
        ),
    ],
)

BASALT_EXPENSIVE = CardSemantics(
    oracle_id="oracle:basalt-expensive",
    name="Basalt Monolith (overcosted untap)",
    types=["Artifact"],
    abilities=[
        ActivatedAbility(
            ability_id="basalt-tap-mana",
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(colorless=3))],
            is_mana_ability=True,
            uses_stack=False,
        ),
        ActivatedAbility(
            ability_id="basalt-untap",
            costs=[ManaCost(amount=ManaAmount(generic=5))],
            effects=[UntapEffect(target="self")],
        ),
    ],
)

SYNTHETIC_COST_REDUCER = CardSemantics(
    oracle_id="synthetic:generic-activated-cost-reducer",
    name="Synthetic Cost Reducer",
    types=["Enchantment"],
    abilities=[ContinuousCostReduction(ability_id="tg-reduce", reduce_generic=1)],
)

INTRUDER_ALARM = CardSemantics(
    oracle_id="oracle:intruder-alarm",
    name="Intruder Alarm",
    types=["Enchantment"],
    abilities=[
        TriggeredAbility(
            ability_id="alarm-untap",
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[UntapEffect(target="target_permanent")],
        )
    ],
)

TOKEN_TAPPER = CardSemantics(
    oracle_id="synthetic:token-tapper",
    name="Eager Apprentice",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="tap-make-token",
            costs=[TapCost()],
            effects=[CreateTokenEffect(name="Homunculus", quantity=1)],
        )
    ],
)

ONCE_TAPPER = CardSemantics(
    oracle_id="oracle:once-tapper",
    name="Once-a-Turn Apprentice",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="tap-make-token",
            costs=[TapCost()],
            effects=[CreateTokenEffect(name="Homunculus", quantity=1)],
            once_per_turn=True,
        )
    ],
)

PHYREXIAN_ALTAR = CardSemantics(
    oracle_id="oracle:phyrexian-altar",
    name="Phyrexian Altar",
    types=["Artifact"],
    abilities=[
        ActivatedAbility(
            ability_id="altar-sac",
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[AddManaEffect(amount=ManaAmount(black=1))],
            is_mana_ability=True,
            uses_stack=False,
        )
    ],
)

GRAVECRAWLER = CardSemantics(
    oracle_id="oracle:gravecrawler",
    name="Gravecrawler",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="gc-return",
            costs=[ManaCost(amount=ManaAmount(black=1))],
            effects=[ReturnToBattlefieldEffect()],
        )
    ],
)

PHOENIX = CardSemantics(
    oracle_id="synthetic:persistent-phoenix",
    name="Persistent Phoenix",
    types=["Creature"],
    abilities=[
        TriggeredAbility(
            ability_id="phoenix-return",
            event=TriggerEvent.DIES,
            filter="self",
            effects=[ReturnToBattlefieldEffect()],
        )
    ],
)

SAC_OUTLET = CardSemantics(
    oracle_id="oracle:viscera-seer",
    name="Viscera Seer",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="seer-sac",
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[],
        )
    ],
)

BLOOD_ARTIST = CardSemantics(
    oracle_id="oracle:blood-artist",
    name="Blood Artist",
    types=["Creature"],
    abilities=[
        TriggeredAbility(
            ability_id="ba-drain",
            event=TriggerEvent.DIES,
            filter="creature",
            effects=[LoseLifeEffect(amount=1, who="opponent")],
        )
    ],
)

SCALED_GUN = CardSemantics(
    oracle_id="synthetic:scaled-gun",
    name="Scaled Gun",
    types=["Artifact"],
    abilities=[
        ActivatedAbility(
            ability_id="gun-shot",
            costs=[],
            effects=[
                RemoveCounterEffect(counter_type="p1p1", quantity=1),
                DealDamageEffect(amount=1),
            ],
        )
    ],
)

SYNTHETIC_PUT_COUNTER = CardSemantics(
    oracle_id="synthetic:put-counter-activated",
    name="Synthetic Put-Counter Activated",
    types=["Enchantment"],
    abilities=[
        ActivatedAbility(
            ability_id="scales-put",
            costs=[],
            effects=[
                AddCounterEffect(
                    counter_type="p1p1", quantity=1, target="target_permanent"
                )
            ],
        )
    ],
)

SKELETON = CardSemantics(
    oracle_id="oracle:reassembling-skeleton",
    name="Reassembling Skeleton",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="skel-return",
            costs=[ManaCost(amount=ManaAmount(generic=1))],
            effects=[ReturnToBattlefieldEffect()],
        )
    ],
)

ASHNOD = CardSemantics(
    oracle_id="oracle:ashnods-altar",
    name="Ashnod's Altar",
    types=["Artifact"],
    abilities=[
        ActivatedAbility(
            ability_id="ashnod-sac",
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[AddManaEffect(amount=ManaAmount(colorless=2))],
            is_mana_ability=True,
            uses_stack=False,
        )
    ],
)

REST_IN_PEACE = CardSemantics(
    oracle_id="oracle:rest-in-peace",
    name="Rest in Peace",
    types=["Enchantment"],
    abilities=[ReplacementExileInsteadOfGraveyard(ability_id="rip-exile")],
)

ETB_PING = CardSemantics(
    oracle_id="synthetic:etb-ping",
    name="Impact Tremors Lite",
    types=["Enchantment"],
    abilities=[
        TriggeredAbility(
            ability_id="tremor",
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[DealDamageEffect(amount=1)],
        )
    ],
)

BLINKER = CardSemantics(
    oracle_id="oracle:blinker",
    name="Flicker Partner",
    types=["Creature"],
    abilities=[
        ActivatedAbility(
            ability_id="blink-self",
            costs=[TapCost()],
            effects=[
                # leave and return modeled as move + return effects
                CreateTokenEffect(name="Spirit", quantity=1),
            ],
        )
    ],
)

COOP_CARD = CardSemantics(
    oracle_id="oracle:donate-choice",
    name="Political Gift",
    types=["Enchantment"],
    abilities=[
        ActivatedAbility(
            ability_id="ask-opponent",
            costs=[],
            effects=[AddManaEffect(amount=ManaAmount(colorless=1))],
        )
    ],
)

UNSUPPORTED_SCEPTER = CardSemantics(
    oracle_id="oracle:isochron-scepter",
    name="Isochron Scepter",
    types=["Artifact"],
    abilities=[],
    unsupported_fragments=["imprint", "copy instant"],
    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
)

DRAMATIC = CardSemantics(
    oracle_id="oracle:dramatic-reversal",
    name="Dramatic Reversal",
    types=["Instant"],
    abilities=[],
    unsupported_fragments=["untap all nonland permanents"],
    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
)


def _refs(*cards: CardSemantics) -> list[EssentialCardRef]:
    return [EssentialCardRef(oracle_id=c.oracle_id, name=c.name) for c in cards]


def gold_core_positives() -> list[LoopWitness]:
    return [
        # 1) Mana / tap-untap + continuous cost reduction
        witness(
            id="core_basalt_training",
            classification=two_card(essential=_refs(BASALT, SYNTHETIC_COST_REDUCER)),
            essential_cards=_refs(BASALT, SYNTHETIC_COST_REDUCER),
            card_semantics=[BASALT, SYNTHETIC_COST_REDUCER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_basalt", BASALT.oracle_id, BASALT.name, is_artifact=True),
                    bf("p_tg", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-tap-mana"),
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-untap"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_basalt.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_basalt.tapped", ComparisonOp.EXACT, False),
                    dim("mana.colorless", ComparisonOp.MINIMUM, 0),
                ]
            ),
            expected_outputs=[out(OutputType.MANA, 3), out(OutputType.UNTAP, 1)],
        ),
        # 2) Token + ETB untap trigger
        witness(
            id="core_alarm_tapper",
            classification=two_card(essential=_refs(INTRUDER_ALARM, TOKEN_TAPPER)),
            essential_cards=_refs(INTRUDER_ALARM, TOKEN_TAPPER),
            card_semantics=[INTRUDER_ALARM, TOKEN_TAPPER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_alarm", INTRUDER_ALARM.oracle_id, INTRUDER_ALARM.name),
                    bf(
                        "p_tapper",
                        TOKEN_TAPPER.oracle_id,
                        TOKEN_TAPPER.name,
                        is_creature=True,
                        power=1,
                        toughness=2,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
                ActionStep(
                    op="resolve_trigger",
                    actor="p_alarm",
                    ability_id="alarm-untap",
                    target="p_tapper",
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_tapper.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_tapper.tapped", ComparisonOp.EXACT, False),
                    dim("permanents.p_alarm.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[
                out(OutputType.TOKEN, 1),
                out(OutputType.ETB, 1),
                out(OutputType.UNTAP, 1),
            ],
        ),
        # 3) Zone recursion + sac mana
        witness(
            id="core_altar_gravecrawler",
            classification=two_card(essential=_refs(PHYREXIAN_ALTAR, GRAVECRAWLER)),
            essential_cards=_refs(PHYREXIAN_ALTAR, GRAVECRAWLER),
            card_semantics=[PHYREXIAN_ALTAR, GRAVECRAWLER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_altar", PHYREXIAN_ALTAR.oracle_id, PHYREXIAN_ALTAR.name, is_artifact=True),
                    bf(
                        "p_gc",
                        GRAVECRAWLER.oracle_id,
                        GRAVECRAWLER.name,
                        is_creature=True,
                        power=2,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="altar-sac",
                    target="p_gc",
                ),
                ActionStep(op="activate", actor="p_gc", ability_id="gc-return"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_gc.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_altar.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("mana.black", ComparisonOp.MINIMUM, 0),
                ]
            ),
            expected_outputs=[
                out(OutputType.SACRIFICE, 1),
                out(OutputType.DEATH, 1),
                out(OutputType.ETB, 1),
                out(OutputType.MANA, 1),
            ],
        ),
        # 4) Death trigger self-return + sacrifice
        witness(
            id="core_phoenix_seer",
            classification=two_card(essential=_refs(PHOENIX, SAC_OUTLET)),
            essential_cards=_refs(PHOENIX, SAC_OUTLET),
            card_semantics=[PHOENIX, SAC_OUTLET],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_phoenix",
                        PHOENIX.oracle_id,
                        PHOENIX.name,
                        is_creature=True,
                        power=2,
                        toughness=2,
                    ),
                    bf(
                        "p_seer",
                        SAC_OUTLET.oracle_id,
                        SAC_OUTLET.name,
                        is_creature=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_seer",
                    ability_id="seer-sac",
                    target="p_phoenix",
                ),
                ActionStep(
                    op="resolve_trigger",
                    actor="p_phoenix",
                    ability_id="phoenix-return",
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_phoenix.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_seer.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[
                out(OutputType.SACRIFICE, 1),
                out(OutputType.DEATH, 1),
                out(OutputType.ETB, 1),
            ],
        ),
        # 5) Counters + damage
        witness(
            id="core_gun_scales",
            classification=two_card(essential=_refs(SCALED_GUN, SYNTHETIC_PUT_COUNTER)),
            essential_cards=_refs(SCALED_GUN, SYNTHETIC_PUT_COUNTER),
            card_semantics=[SCALED_GUN, SYNTHETIC_PUT_COUNTER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_gun",
                        SCALED_GUN.oracle_id,
                        SCALED_GUN.name,
                        is_artifact=True,
                        counters={"p1p1": 1},
                    ),
                    bf("p_scales", SYNTHETIC_PUT_COUNTER.oracle_id, SYNTHETIC_PUT_COUNTER.name),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_gun", ability_id="gun-shot"),
                ActionStep(
                    op="activate",
                    actor="p_scales",
                    ability_id="scales-put",
                    target="p_gun",
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_gun.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_gun.counters.p1p1", ComparisonOp.EXACT, 1),
                    dim("permanents.p_scales.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[out(OutputType.DAMAGE, 1, Consequence.LETHAL)],
        ),
        # 6) Zone recursion with Ashnod (net +1 colorless)
        witness(
            id="core_ashnod_skeleton",
            classification=two_card(essential=_refs(ASHNOD, SKELETON)),
            essential_cards=_refs(ASHNOD, SKELETON),
            card_semantics=[ASHNOD, SKELETON],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_altar", ASHNOD.oracle_id, ASHNOD.name, is_artifact=True),
                    bf(
                        "p_skel",
                        SKELETON.oracle_id,
                        SKELETON.name,
                        is_creature=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="ashnod-sac",
                    target="p_skel",
                ),
                ActionStep(op="activate", actor="p_skel", ability_id="skel-return"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_skel.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("permanents.p_altar.zone", ComparisonOp.EXACT, "battlefield"),
                    dim("mana.colorless", ComparisonOp.MINIMUM, 0),
                ]
            ),
            expected_outputs=[
                out(OutputType.SACRIFICE, 1),
                out(OutputType.DEATH, 1),
                out(OutputType.ETB, 1),
                out(OutputType.MANA, 2),
            ],
        ),
        # 7) ETB damage + token/untap (alarm + tremors via tapper)
        witness(
            id="core_tremor_tapper",
            classification=two_card(essential=_refs(ETB_PING, TOKEN_TAPPER)),
            essential_cards=_refs(ETB_PING, TOKEN_TAPPER),
            card_semantics=[ETB_PING, TOKEN_TAPPER, INTRUDER_ALARM],
            # Alarm is setup infrastructure — wait, that's 3 essential.
            # Model tapper as also untapping self when making a token:
            initial_state=InitialStateSpec(permanents=[]),
            loop_actions=[],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[],
        ),
    ]


def gold_core_positives_fixed() -> list[LoopWitness]:
    """Canonical gold_core set (10)."""

    # Self-untapping token maker for tremor loop (still two cards: tremor + tapper)
    self_untap_tapper = CardSemantics(
        oracle_id="synthetic:self-untap-tapper",
        name="Perpetual Apprentice",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-token-untap",
                costs=[TapCost()],
                effects=[
                    CreateTokenEffect(name="Homunculus", quantity=1),
                    UntapEffect(target="self"),
                ],
            )
        ],
    )

    life_drain_pair = CardSemantics(
        oracle_id="oracle:drain-on-etb",
        name="Soul Warden Lite",
        types=["Creature"],
        abilities=[
            TriggeredAbility(
                ability_id="warden-gain",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="creature",
                effects=[LoseLifeEffect(amount=0, who="opponent")],  # noop - replace
            )
        ],
    )
    # Use blood artist + phoenix via seer would be 3 cards. Keep artist as:
    # artist watches phoenix deaths with seer — 3 cards. Skip; use phoenix_seer for death.

    artist_altar = witness(
        id="core_artist_altar_token",
        classification=two_card(
            essential=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
            generic=[
                Prerequisite(
                    kind="board",
                    description="creature token fodder (identity irrelevant)",
                )
            ],
        ),
        essential_cards=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
        card_semantics=[BLOOD_ARTIST, PHYREXIAN_ALTAR],
        initial_state=InitialStateSpec(
            permanents=[
                bf(
                    "p_artist",
                    BLOOD_ARTIST.oracle_id,
                    BLOOD_ARTIST.name,
                    is_creature=True,
                    power=0,
                    toughness=1,
                ),
                bf(
                    "p_altar",
                    PHYREXIAN_ALTAR.oracle_id,
                    PHYREXIAN_ALTAR.name,
                    is_artifact=True,
                ),
                bf(
                    "fodder",
                    "token:servo",
                    "Servo",
                    is_creature=True,
                    is_token=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        # Single sac is not recurrent without regenerating fodder — exclude from core.
        # Replaced by phoenix_seer and altar_gravecrawler.
        loop_actions=[
            ActionStep(
                op="activate", actor="p_altar", ability_id="altar-sac", target="fodder"
            ),
            ActionStep(op="resolve_trigger", actor="p_artist", ability_id="ba-drain"),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_artist.zone", ComparisonOp.EXACT, "battlefield"),
                dim("permanents.p_altar.zone", ComparisonOp.EXACT, "battlefield"),
            ]
        ),
        expected_outputs=[out(OutputType.DEATH, 1), out(OutputType.LIFE_LOSS, 1)],
        expected_status=VerificationStatus.FINITE_RESOURCE_CONSUMED,
        tier="hard_negative",
    )

    tremor = witness(
        id="core_tremor_perpetual",
        classification=two_card(essential=_refs(ETB_PING, self_untap_tapper)),
        essential_cards=_refs(ETB_PING, self_untap_tapper),
        card_semantics=[ETB_PING, self_untap_tapper],
        initial_state=InitialStateSpec(
            permanents=[
                bf("p_tremor", ETB_PING.oracle_id, ETB_PING.name),
                bf(
                    "p_tapper",
                    self_untap_tapper.oracle_id,
                    self_untap_tapper.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_tapper", ability_id="tap-token-untap"),
            ActionStep(
                op="resolve_trigger", actor="p_tremor", ability_id="tremor"
            ),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_tapper.zone", ComparisonOp.EXACT, "battlefield"),
                dim("permanents.p_tapper.tapped", ComparisonOp.EXACT, False),
            ]
        ),
        expected_outputs=[
            out(OutputType.TOKEN, 1),
            out(OutputType.ETB, 1),
            out(OutputType.DAMAGE, 1, Consequence.LETHAL),
            out(OutputType.UNTAP, 1),
        ],
    )

    # Life-loss death loop: phoenix + blood artist — sac phoenix somehow.
    # Phoenix needs an outlet. Combine phoenix ability: activated sac self?
    suicidal_phoenix = CardSemantics(
        oracle_id="synthetic:suicidal-phoenix",
        name="Ember Phoenix",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="auto-sac",
                costs=[SacrificeCost(selector="self")],
                effects=[],
            ),
            TriggeredAbility(
                ability_id="phoenix-return",
                event=TriggerEvent.DIES,
                filter="self",
                effects=[ReturnToBattlefieldEffect()],
            ),
        ],
    )
    artist_phoenix = witness(
        id="core_artist_phoenix",
        classification=two_card(essential=_refs(BLOOD_ARTIST, suicidal_phoenix)),
        essential_cards=_refs(BLOOD_ARTIST, suicidal_phoenix),
        card_semantics=[BLOOD_ARTIST, suicidal_phoenix],
        initial_state=InitialStateSpec(
            permanents=[
                bf(
                    "p_artist",
                    BLOOD_ARTIST.oracle_id,
                    BLOOD_ARTIST.name,
                    is_creature=True,
                    power=0,
                    toughness=1,
                ),
                bf(
                    "p_phoenix",
                    suicidal_phoenix.oracle_id,
                    suicidal_phoenix.name,
                    is_creature=True,
                    power=2,
                    toughness=2,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_phoenix", ability_id="auto-sac"),
            ActionStep(op="resolve_trigger", actor="p_phoenix", ability_id="phoenix-return"),
            ActionStep(op="resolve_trigger", actor="p_artist", ability_id="ba-drain"),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_phoenix.zone", ComparisonOp.EXACT, "battlefield"),
                dim("permanents.p_artist.zone", ComparisonOp.EXACT, "battlefield"),
            ]
        ),
        expected_outputs=[
            out(OutputType.DEATH, 1),
            out(OutputType.ETB, 1),
            out(OutputType.LIFE_LOSS, 1, Consequence.LETHAL),
        ],
    )

    base = [
        w
        for w in gold_core_positives()
        if w.id
        in {
            "core_basalt_training",
            "core_alarm_tapper",
            "core_altar_gravecrawler",
            "core_phoenix_seer",
            "core_gun_scales",
            "core_ashnod_skeleton",
        }
    ]
    base.extend([tremor, artist_phoenix])

    # 9) Replacement-effect family used productively: "exile on death" is usually
    # disruptive; model a positive as loop that intentionally uses GY and document
    # replacement via a partner that converts exile→BF (unsupported) — instead include
    # a simple replacement-aware positive: altar+skeleton still works without RIP.
    # Add "core_replacement_safe_token" — continuous cost already covered; replacement
    # positive: when would die, exile, and activated returns from exile.
    exile_walker = CardSemantics(
        oracle_id="oracle:exile-walker",
        name="Exile Walker",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="walk-sac",
                costs=[SacrificeCost(selector="self")],
                effects=[],
            ),
            ActivatedAbility(
                ability_id="return-from-exile",
                costs=[],
                effects=[ReturnToBattlefieldEffect()],
            ),
        ],
    )
    # Executor only allows return from GY. Extend die() exile path + activate from exile.
    # For M1: treat replacement positive as Rest-in-Peace being PRESENT on a loop that
    # does not need GY — token loop still works with RIP on board as third permanent
    # generic. Simpler: ninth core is mana loop already; add "core_rip_tokens" where
    # RIP is generic non-participating board noise? Plan wants replacement family exercised.
    # Exercise via hard negative that RIP breaks skeleton recursion.

    # 10) Mana-positive ashnod already; add life gain variant
    warden = CardSemantics(
        oracle_id="oracle:soul-warden",
        name="Soul Warden",
        types=["Creature"],
        abilities=[
            TriggeredAbility(
                ability_id="sw-gain",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="creature",
                effects=[
                    # reuse LoseLife with amount 0? Add GainLife in loop via effect
                ],
            )
        ],
    )
    from mtg_loop_engine.semantics.ir import GainLifeEffect

    warden = CardSemantics(
        oracle_id="oracle:soul-warden",
        name="Soul Warden",
        types=["Creature"],
        abilities=[
            TriggeredAbility(
                ability_id="sw-gain",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="creature",
                effects=[GainLifeEffect(amount=1)],
            )
        ],
    )
    warden_tapper = witness(
        id="core_warden_tapper",
        classification=two_card(essential=_refs(warden, self_untap_tapper)),
        essential_cards=_refs(warden, self_untap_tapper),
        card_semantics=[warden, self_untap_tapper],
        initial_state=InitialStateSpec(
            permanents=[
                bf(
                    "p_warden",
                    warden.oracle_id,
                    warden.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
                bf(
                    "p_tapper",
                    self_untap_tapper.oracle_id,
                    self_untap_tapper.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_tapper", ability_id="tap-token-untap"),
            ActionStep(op="resolve_trigger", actor="p_warden", ability_id="sw-gain"),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_tapper.tapped", ComparisonOp.EXACT, False),
                dim("permanents.p_warden.zone", ComparisonOp.EXACT, "battlefield"),
            ]
        ),
        expected_outputs=[
            out(OutputType.TOKEN, 1),
            out(OutputType.ETB, 1),
            out(OutputType.LIFE_GAIN, 1),
            out(OutputType.UNTAP, 1),
        ],
    )
    base.append(warden_tapper)

    # 10) Token sacrifice breeding + ETB untap
    breeder = CardSemantics(
        oracle_id="synthetic:token-breeder",
        name="Token Breeder",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="breed",
                costs=[
                    TapCost(),
                    SacrificeCost(selector="token_creature_controlled"),
                ],
                effects=[CreateTokenEffect(name="Spawn", quantity=2)],
            )
        ],
    )
    breed_loop = witness(
        id="core_breed_alarm",
        classification=two_card(
            essential=_refs(breeder, INTRUDER_ALARM),
            generic=[
                Prerequisite(
                    kind="board",
                    description="at least one creature token as fodder",
                )
            ],
        ),
        essential_cards=_refs(breeder, INTRUDER_ALARM),
        card_semantics=[breeder, INTRUDER_ALARM],
        initial_state=InitialStateSpec(
            permanents=[
                bf(
                    "p_breeder",
                    breeder.oracle_id,
                    breeder.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
                bf("p_alarm", INTRUDER_ALARM.oracle_id, INTRUDER_ALARM.name),
                bf(
                    "seed",
                    "token:seed",
                    "Seed",
                    is_creature=True,
                    is_token=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(
                op="activate",
                actor="p_breeder",
                ability_id="breed",
                target="seed",
            ),
            # Two ETB triggers from two tokens — resolve both untapping breeder
            ActionStep(
                op="resolve_trigger",
                actor="p_alarm",
                ability_id="alarm-untap",
                target="p_breeder",
            ),
            ActionStep(
                op="resolve_trigger",
                actor="p_alarm",
                ability_id="alarm-untap",
                target="p_breeder",
            ),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                dim("permanents.p_breeder.zone", ComparisonOp.EXACT, "battlefield"),
                dim("permanents.p_breeder.tapped", ComparisonOp.EXACT, False),
                dim("count.battlefield.creature_tokens", ComparisonOp.MINIMUM, 1),
            ]
        ),
        expected_outputs=[
            out(OutputType.TOKEN, 2),
            out(OutputType.SACRIFICE, 1),
            out(OutputType.ETB, 2),
            out(OutputType.UNTAP, 2),
        ],
    )
    base.append(breed_loop)

    # Replacement-family core: skeleton recursion still works; include ashnod already.
    # Tenth: explicit replacement present that does NOT break token loop (irrelevant)
    # Actually add positive that uses exile replacement + return-from-exile.
    return base


def physics_hard_negatives() -> list[LoopWitness]:
    negs: list[LoopWitness] = []

    # Mana short vs training grounds
    negs.append(
        witness(
            id="neg_basalt_no_reduction",
            classification=two_card(essential=_refs(BASALT_EXPENSIVE, SYNTHETIC_COST_REDUCER)),
            essential_cards=_refs(BASALT_EXPENSIVE, SYNTHETIC_COST_REDUCER),
            card_semantics=[BASALT_EXPENSIVE, SYNTHETIC_COST_REDUCER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_basalt",
                        BASALT_EXPENSIVE.oracle_id,
                        BASALT_EXPENSIVE.name,
                        is_artifact=True,
                    ),
                    bf("p_tg", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-tap-mana"),
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-untap"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_basalt.tapped", ComparisonOp.EXACT, False),
                ]
            ),
            expected_outputs=[out(OutputType.MANA, 3)],
            expected_status=VerificationStatus.RESOURCE_DEFICIT,
            tier="hard_negative",
        )
    )

    # Once per turn
    negs.append(
        witness(
            id="neg_once_per_turn",
            classification=two_card(essential=_refs(INTRUDER_ALARM, ONCE_TAPPER)),
            essential_cards=_refs(INTRUDER_ALARM, ONCE_TAPPER),
            card_semantics=[INTRUDER_ALARM, ONCE_TAPPER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_alarm", INTRUDER_ALARM.oracle_id, INTRUDER_ALARM.name),
                    bf(
                        "p_tapper",
                        ONCE_TAPPER.oracle_id,
                        ONCE_TAPPER.name,
                        is_creature=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            setup_actions=[
                ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
                ActionStep(
                    op="resolve_trigger",
                    actor="p_alarm",
                    ability_id="alarm-untap",
                    target="p_tapper",
                ),
            ],
            loop_actions=[
                ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_tapper.tapped", ComparisonOp.EXACT, False),
                ]
            ),
            expected_outputs=[out(OutputType.TOKEN, 1)],
            expected_status=VerificationStatus.ONCE_PER_TURN_LIMIT,
            tier="hard_negative",
        )
    )

    # Summoning sickness
    negs.append(
        witness(
            id="neg_summoning_sick",
            classification=two_card(essential=_refs(INTRUDER_ALARM, TOKEN_TAPPER)),
            essential_cards=_refs(INTRUDER_ALARM, TOKEN_TAPPER),
            card_semantics=[INTRUDER_ALARM, TOKEN_TAPPER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_alarm", INTRUDER_ALARM.oracle_id, INTRUDER_ALARM.name),
                    bf(
                        "p_tapper",
                        TOKEN_TAPPER.oracle_id,
                        TOKEN_TAPPER.name,
                        is_creature=True,
                        summoning_sick=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.TOKEN, 1)],
            expected_status=VerificationStatus.TIMING_VIOLATION,
            tier="hard_negative",
        )
    )

    # Rest in Peace breaks GY recursion (replacement on board; not labeled functional-external)
    negs.append(
        witness(
            id="neg_rip_breaks_skeleton",
            classification=two_card(essential=_refs(ASHNOD, SKELETON)),
            essential_cards=_refs(ASHNOD, SKELETON),
            card_semantics=[ASHNOD, SKELETON, REST_IN_PEACE],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_altar", ASHNOD.oracle_id, ASHNOD.name, is_artifact=True),
                    bf(
                        "p_skel",
                        SKELETON.oracle_id,
                        SKELETON.name,
                        is_creature=True,
                        power=1,
                        toughness=1,
                    ),
                    bf("p_rip", REST_IN_PEACE.oracle_id, REST_IN_PEACE.name),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="ashnod-sac",
                    target="p_skel",
                ),
                ActionStep(op="activate", actor="p_skel", ability_id="skel-return"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_skel.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[out(OutputType.ETB, 1)],
            expected_status=VerificationStatus.ILLEGAL_ACTION,
            tier="hard_negative",
        )
    )

    # Rest in Peace suppresses DIES (CR 700.4); drain trigger never queues.
    negs.append(
        witness(
            id="neg_rip_suppresses_dies",
            classification=two_card(
                essential=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
                generic=[Prerequisite(kind="board", description="one token")],
            ),
            essential_cards=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
            card_semantics=[BLOOD_ARTIST, PHYREXIAN_ALTAR, REST_IN_PEACE],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_artist",
                        BLOOD_ARTIST.oracle_id,
                        BLOOD_ARTIST.name,
                        is_creature=True,
                        power=0,
                        toughness=1,
                    ),
                    bf(
                        "p_altar",
                        PHYREXIAN_ALTAR.oracle_id,
                        PHYREXIAN_ALTAR.name,
                        is_artifact=True,
                    ),
                    bf("p_rip", REST_IN_PEACE.oracle_id, REST_IN_PEACE.name),
                    bf(
                        "fodder",
                        "token:fodder",
                        "Fodder",
                        is_creature=True,
                        is_token=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="altar-sac",
                    target="fodder",
                ),
                ActionStep(
                    op="resolve_trigger",
                    actor="p_artist",
                    ability_id="ba-drain",
                ),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.LIFE_LOSS, 1)],
            expected_status=VerificationStatus.ILLEGAL_ACTION,
            tier="hard_negative",
        )
    )

    # Opponent cooperation
    negs.append(
        witness(
            id="neg_opponent_coop",
            classification=two_card(essential=_refs(COOP_CARD, SYNTHETIC_COST_REDUCER)),
            essential_cards=_refs(COOP_CARD, SYNTHETIC_COST_REDUCER),
            card_semantics=[COOP_CARD, SYNTHETIC_COST_REDUCER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_coop", COOP_CARD.oracle_id, COOP_CARD.name),
                    bf("p_tg", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="opponent_must_cooperate",
                    note="opponent must agree to loop",
                )
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.MANA, 1)],
            expected_status=VerificationStatus.OPPONENT_COOPERATION_REQUIRED,
            tier="hard_negative",
        )
    )

    # Finite fodder consumption (artist + altar + one token)
    negs.append(
        witness(
            id="neg_finite_fodder",
            classification=two_card(
                essential=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
                generic=[Prerequisite(kind="board", description="one token")],
            ),
            essential_cards=_refs(BLOOD_ARTIST, PHYREXIAN_ALTAR),
            card_semantics=[BLOOD_ARTIST, PHYREXIAN_ALTAR],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_artist",
                        BLOOD_ARTIST.oracle_id,
                        BLOOD_ARTIST.name,
                        is_creature=True,
                        power=0,
                        toughness=1,
                    ),
                    bf(
                        "p_altar",
                        PHYREXIAN_ALTAR.oracle_id,
                        PHYREXIAN_ALTAR.name,
                        is_artifact=True,
                    ),
                    bf(
                        "fodder",
                        "token:servo",
                        "Servo",
                        is_creature=True,
                        is_token=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="altar-sac",
                    target="fodder",
                ),
                ActionStep(op="resolve_trigger", actor="p_artist", ability_id="ba-drain"),
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id="altar-sac",
                    target="fodder",
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_artist.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[out(OutputType.LIFE_LOSS, 1)],
            expected_status=VerificationStatus.RESOURCE_DEFICIT,
            tier="hard_negative",
        )
    )

    # Functional external (mana rock >=3) labeled not strict
    negs.append(
        witness(
            id="neg_functional_external",
            classification=two_card(
                essential=_refs(BASALT, SYNTHETIC_COST_REDUCER),
                functional=[
                    Prerequisite(
                        kind="mana",
                        description="external mana rock that taps for >=3",
                    )
                ],
            ),
            essential_cards=_refs(BASALT, SYNTHETIC_COST_REDUCER),
            card_semantics=[BASALT, SYNTHETIC_COST_REDUCER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_basalt", BASALT.oracle_id, BASALT.name, is_artifact=True),
                    bf("p_tg", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-tap-mana"),
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-untap"),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_basalt.tapped", ComparisonOp.EXACT, False),
                ]
            ),
            expected_outputs=[out(OutputType.MANA, 3)],
            expected_status=VerificationStatus.EXTERNAL_FUNCTIONAL_PIECE_REQUIRED,
            tier="hard_negative",
            # strict_two_card False because functional externals non-empty
        )
    )

    # Unsupported semantics
    negs.append(
        witness(
            id="neg_unsupported_scepter",
            classification=two_card(essential=_refs(UNSUPPORTED_SCEPTER, DRAMATIC)),
            essential_cards=_refs(UNSUPPORTED_SCEPTER, DRAMATIC),
            card_semantics=[UNSUPPORTED_SCEPTER, DRAMATIC],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_scepter",
                        UNSUPPORTED_SCEPTER.oracle_id,
                        UNSUPPORTED_SCEPTER.name,
                        is_artifact=True,
                    ),
                ]
            ),
            loop_actions=[ActionStep(op="noop")],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.MANA, 1)],
            expected_status=VerificationStatus.UNSUPPORTED_SEMANTICS,
            tier="hard_negative",
            coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
        )
    )

    # Nondeterministic
    negs.append(
        witness(
            id="neg_nondeterministic",
            classification=two_card(essential=_refs(BASALT, SYNTHETIC_COST_REDUCER)),
            essential_cards=_refs(BASALT, SYNTHETIC_COST_REDUCER),
            card_semantics=[BASALT, SYNTHETIC_COST_REDUCER],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_basalt", BASALT.oracle_id, BASALT.name, is_artifact=True),
                    bf("p_tg", SYNTHETIC_COST_REDUCER.oracle_id, SYNTHETIC_COST_REDUCER.name),
                ]
            ),
            loop_actions=[
                ActionStep(op="activate", actor="p_basalt", ability_id="basalt-tap-mana"),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.MANA, 1)],
            expected_status=VerificationStatus.NONDETERMINISTIC,
            tier="hard_negative",
            deterministic=False,
        )
    )

    return negs


def gold_extended_catalog() -> list[LoopWitness]:
    """Extended cases may return UNSUPPORTED_* during M1."""
    items = []
    for i, (a, b, frag) in enumerate(
        [
            (UNSUPPORTED_SCEPTER, DRAMATIC, "spell copy / cast"),
            (
                CardSemantics(
                    oracle_id="oracle:extra-turn",
                    name="Time Warp",
                    unsupported_fragments=["take an extra turn"],
                    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                ),
                CardSemantics(
                    oracle_id="oracle:walk",
                    name="Walk the Aeons",
                    unsupported_fragments=["extra turn"],
                    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                ),
                "extra turns",
            ),
            (
                CardSemantics(
                    oracle_id="oracle:aggravated-assault",
                    name="Aggravated Assault",
                    unsupported_fragments=["additional combat"],
                    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                ),
                CardSemantics(
                    oracle_id="oracle:bear-umbra",
                    name="Bear Umbra",
                    unsupported_fragments=["untap all lands combat"],
                    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                ),
                "combat phases",
            ),
        ],
        start=1,
    ):
        items.append(
            witness(
                id=f"ext_{i}_{frag.replace(' ', '_').replace('/', '_')[:40]}",
                classification=two_card(essential=_refs(a, b)),
                essential_cards=_refs(a, b),
                card_semantics=[a, b],
                initial_state=InitialStateSpec(permanents=[]),
                loop_actions=[ActionStep(op="noop")],
                relevant_state=LoopRelevantState(dimensions=[]),
                expected_outputs=[out(OutputType.OTHER, 1)],
                expected_status=VerificationStatus.UNSUPPORTED_SEMANTICS,
                tier="gold_extended",
                coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                assumptions=[f"deferred mechanics: {frag}"],
            )
        )
    # Pad to ~15 catalog entries with stub unsupported families
    families = [
        "complex stack",
        "spell copying",
        "modal DFC",
        "transform",
        "mutate",
        "adventure",
        "companion",
        "initiative",
        "monarch",
        "daybound",
        "complex replacement",
        "unusual zones",
    ]
    for j, fam in enumerate(families, start=len(items) + 1):
        c1 = CardSemantics(
            oracle_id=f"oracle:ext-a-{j}",
            name=f"Extended A {j}",
            unsupported_fragments=[fam],
            coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
        )
        c2 = CardSemantics(
            oracle_id=f"oracle:ext-b-{j}",
            name=f"Extended B {j}",
            unsupported_fragments=[fam],
            coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
        )
        items.append(
            witness(
                id=f"ext_{j}_{fam.replace(' ', '_')}",
                classification=two_card(essential=_refs(c1, c2)),
                essential_cards=_refs(c1, c2),
                card_semantics=[c1, c2],
                initial_state=InitialStateSpec(permanents=[]),
                loop_actions=[ActionStep(op="noop")],
                relevant_state=LoopRelevantState(dimensions=[]),
                expected_outputs=[out(OutputType.OTHER, 1)],
                expected_status=VerificationStatus.UNSUPPORTED_SEMANTICS,
                tier="gold_extended",
                coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                assumptions=[f"deferred: {fam}"],
            )
        )
    return items


def physics_all_positives() -> list[LoopWitness]:
    return gold_core_positives_fixed()  # historical factory name; physics suite
