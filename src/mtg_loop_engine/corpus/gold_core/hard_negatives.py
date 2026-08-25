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

    return negs


__all__ = ["hard_negatives"]
