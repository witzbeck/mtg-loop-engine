"""Oracle-exact hard negatives for Wave 1 gold promotions."""

from __future__ import annotations

from mtg_loop_engine.corpus.builders import (
    ActionStep,
    ComparisonOp,
    InitialStateSpec,
    LoopRelevantState,
    OutputType,
    Prerequisite,
    VerificationStatus,
    bf,
    dim,
    out,
    two_card,
    witness,
)
from mtg_loop_engine.proofs.models import EssentialCardRef, LoopWitness
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def _compile(oracle_id: str):
    fix = GOLD_ORACLE_FIXTURES[oracle_id]
    return compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    ).semantics


def _refs(*cards) -> list[EssentialCardRef]:
    return [EssentialCardRef(oracle_id=c.oracle_id, name=c.name) for c in cards]


def hard_negatives() -> list[LoopWitness]:
    """Counterfactuals paired with Wave 1 Oracle gold."""
    negs: list[LoopWitness] = []

    altar = _compile("oracle:phyrexian-altar")
    gc = _compile("oracle:gravecrawler")
    # Gravecrawler without another Zombie → illegal GY cast.
    negs.append(
        witness(
            id="neg_gravecrawler_no_zombie",
            classification=two_card(essential=_refs(altar, gc)),
            essential_cards=_refs(altar, gc),
            card_semantics=[altar, gc],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_gc",
                        gc.oracle_id,
                        gc.name,
                        is_creature=True,
                        power=2,
                        toughness=1,
                    ),
                    bf("p_altar", altar.oracle_id, altar.name, is_artifact=True),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_altar",
                    ability_id=next(
                        a.ability_id for a in altar.abilities if getattr(a, "costs", None)
                    ),
                    target="p_gc",
                ),
                ActionStep(
                    op="activate",
                    actor="p_gc",
                    ability_id=next(
                        a.ability_id
                        for a in gc.abilities
                        if getattr(a, "requires_zombie", False)
                    ),
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_gc.zone", ComparisonOp.EXACT, "battlefield"),
                ]
            ),
            expected_outputs=[out(OutputType.MANA, 1)],
            expected_status=VerificationStatus.ILLEGAL_ACTION,
            tier="hard_negative",
            assumptions=["no Zombie on board after sac"],
        )
    )

    doom = _compile("oracle:thraben-doomsayer")
    alarm = _compile("oracle:intruder-alarm")
    # Summoning-sick Doomsayer cannot tap for the token.
    negs.append(
        witness(
            id="neg_doomsayer_summoning_sick",
            classification=two_card(essential=_refs(alarm, doom)),
            essential_cards=_refs(alarm, doom),
            card_semantics=[alarm, doom],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_alarm", alarm.oracle_id, alarm.name),
                    bf(
                        "p_doom",
                        doom.oracle_id,
                        doom.name,
                        is_creature=True,
                        summoning_sick=True,
                        power=2,
                        toughness=2,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_doom",
                    ability_id=next(
                        a.ability_id for a in doom.abilities if getattr(a, "costs", None)
                    ),
                ),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.TOKEN, 1)],
            expected_status=VerificationStatus.TIMING_VIOLATION,
            tier="hard_negative",
        )
    )

    bond = _compile("oracle:sanguine-bond")
    blood = _compile("oracle:exquisite-blood")
    # Bond/Blood without seed: dormant (no loop actions that can start).
    negs.append(
        witness(
            id="neg_bond_blood_no_seed",
            classification=two_card(
                essential=_refs(bond, blood),
                generic=[
                    Prerequisite(
                        kind="board",
                        description="intentionally omit life-gain seed",
                    )
                ],
            ),
            essential_cards=_refs(bond, blood),
            card_semantics=[bond, blood],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_bond", bond.oracle_id, bond.name),
                    bf("p_blood", blood.oracle_id, blood.name),
                ]
            ),
            loop_actions=[ActionStep(op="noop")],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.LIFE_LOSS, 1)],
            expected_status=VerificationStatus.NOT_A_LOOP,
            tier="hard_negative",
            assumptions=["no life-gain seed → dormant interaction"],
        )
    )

    negs.extend(_wave2_hard_negatives())
    return negs


def _wave2_hard_negatives() -> list[LoopWitness]:
    """Counterfactuals for Wave 2 Oracle gold."""
    negs: list[LoopWitness] = []

    basalt = _compile("oracle:basalt-monolith")
    # Untap without cost reduction and without paying {3}.
    negs.append(
        witness(
            id="neg_basalt_untap_unpaid",
            classification=two_card(essential=_refs(basalt)),
            essential_cards=_refs(basalt),
            card_semantics=[basalt],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_basalt",
                        basalt.oracle_id,
                        basalt.name,
                        is_artifact=True,
                        tapped=True,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_basalt",
                    ability_id=next(
                        a.ability_id
                        for a in basalt.abilities
                        if "untap" in a.ability_id
                    ),
                ),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.UNTAP, 1)],
            expected_status=VerificationStatus.RESOURCE_DEFICIT,
            tier="hard_negative",
            assumptions=["no Zirda cost reduction; untap unpaid"],
        )
    )

    druid = _compile("oracle:devoted-druid")
    # Without Vizier, m1m1 untap eventually can't pay (or dies); single untap alone
    # is not a net-mana loop — claim mana with only untap.
    negs.append(
        witness(
            id="neg_druid_untap_only_no_mana",
            classification=two_card(essential=_refs(druid)),
            essential_cards=_refs(druid),
            card_semantics=[druid],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_druid",
                        druid.oracle_id,
                        druid.name,
                        is_creature=True,
                        power=0,
                        toughness=2,
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_druid",
                    ability_id=next(
                        a.ability_id
                        for a in druid.abilities
                        if "m1m1" in a.ability_id or "untap" in a.ability_id
                    ),
                ),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.MANA, 1)],
            expected_status=VerificationStatus.NOT_A_LOOP,
            tier="hard_negative",
            assumptions=["untap-only without Vizier does not produce mana"],
        )
    )

    rosie = _compile("oracle:rosie-cotton-of-south-lane")
    # Rosie alone: CREATE_TOKEN trigger has no legal other creature target.
    negs.append(
        witness(
            id="neg_rosie_no_other_creature",
            classification=two_card(essential=_refs(rosie)),
            essential_cards=_refs(rosie),
            card_semantics=[rosie],
            initial_state=InitialStateSpec(
                permanents=[
                    bf(
                        "p_rosie",
                        rosie.oracle_id,
                        rosie.name,
                        is_creature=True,
                        power=1,
                        toughness=1,
                    ),
                ]
            ),
            setup_actions=[
                ActionStep(
                    op="seed_create_token",
                    actor="p_rosie",
                    note="seed with no other creature",
                )
            ],
            loop_actions=[
                ActionStep(
                    op="resolve_trigger",
                    actor="p_rosie",
                    ability_id=next(
                        a.ability_id
                        for a in rosie.abilities
                        if getattr(a, "event", None)
                        and a.event.value == "create_token"
                    ),
                    target="p_rosie",
                ),
            ],
            relevant_state=LoopRelevantState(dimensions=[]),
            expected_outputs=[out(OutputType.TOKEN, 1)],
            expected_status=VerificationStatus.ILLEGAL_TARGET,
            tier="hard_negative",
            assumptions=["Rosie cannot put counters on herself"],
        )
    )

    heliod = _compile("oracle:heliod-sun-crowned")
    ballista = _compile("oracle:walking-ballista")
    # Ping without lifelink: no life gain → Heliod does not reload the counter.
    negs.append(
        witness(
            id="neg_ballista_no_lifelink",
            classification=two_card(essential=_refs(heliod, ballista)),
            essential_cards=_refs(heliod, ballista),
            card_semantics=[heliod, ballista],
            initial_state=InitialStateSpec(
                permanents=[
                    bf("p_heliod", heliod.oracle_id, heliod.name, is_creature=True),
                    bf(
                        "p_ballista",
                        ballista.oracle_id,
                        ballista.name,
                        is_creature=True,
                        is_artifact=True,
                        power=0,
                        toughness=0,
                        counters={"p1p1": 1},
                    ),
                ]
            ),
            loop_actions=[
                ActionStep(
                    op="activate",
                    actor="p_ballista",
                    ability_id=next(
                        a.ability_id
                        for a in ballista.abilities
                        if "counter-ping" in a.ability_id
                    ),
                    target="opponent",
                ),
            ],
            relevant_state=LoopRelevantState(
                dimensions=[
                    dim("permanents.p_ballista.counters.p1p1", ComparisonOp.EXACT, 1),
                ]
            ),
            expected_outputs=[out(OutputType.DAMAGE, 1)],
            expected_status=VerificationStatus.STATE_NOT_RECURRENT,
            tier="hard_negative",
            assumptions=["no lifelink grant → counter not replaced"],
        )
    )

    return negs


__all__ = ["hard_negatives"]
