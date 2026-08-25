"""Verifier-owned mandatory LoopRelevantState dimensions (ADR 0008).

Search may propose additional dimensions via ``derive_relevant_state``. The
verifier always merges these mandatory dims (mandatory wins on path conflict)
before recurrence checks, so omitting them from a hand-authored witness cannot
bypass physics.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import (
    ActionStep,
    LoopRelevantState,
    LoopWitness,
    StateDimension,
)
from mtg_loop_engine.semantics.enums import ComparisonOp
from mtg_loop_engine.semantics.ir import ActivatedAbility, CardSemantics
from mtg_loop_engine.state.game import GameState


def once_per_turn_dimensions(
    *,
    loop_actions: list[ActionStep],
    cards: list[CardSemantics],
    before: GameState,
) -> list[StateDimension]:
    """EXACT recurrence for each once-per-turn ability activated in the loop."""
    by_oracle = {c.oracle_id: c for c in cards}
    dims: list[StateDimension] = []
    seen: set[tuple[str, str]] = set()
    for step in loop_actions:
        if step.op != "activate" or not step.actor or not step.ability_id:
            continue
        key = (step.actor, step.ability_id)
        if key in seen:
            continue
        live = before.permanents.get(step.actor)
        if live is None:
            continue
        card = by_oracle.get(live.oracle_id)
        if card is None:
            continue
        for ab in card.abilities:
            if (
                isinstance(ab, ActivatedAbility)
                and ab.ability_id == step.ability_id
                and ab.once_per_turn
            ):
                seen.add(key)
                dims.append(
                    StateDimension(
                        path=(
                            f"permanents.{step.actor}"
                            f".once_per_turn_used.{step.ability_id}"
                        ),
                        op=ComparisonOp.EXACT,
                        value=step.ability_id in live.once_per_turn_used,
                    )
                )
                break
    return dims


def pending_trigger_dimensions(before: GameState) -> list[StateDimension]:
    """Pending trigger queue depth must recur (search already refuses non-empty ends)."""
    return [
        StateDimension(
            path="pending_triggers.count",
            op=ComparisonOp.EXACT,
            value=len(before.pending_triggers),
        )
    ]


def mandatory_recurrence_dimensions(
    witness: LoopWitness, before: GameState
) -> list[StateDimension]:
    return once_per_turn_dimensions(
        loop_actions=witness.loop_actions,
        cards=witness.card_semantics,
        before=before,
    ) + pending_trigger_dimensions(before)


def effective_relevant_state(
    witness: LoopWitness, before: GameState
) -> LoopRelevantState:
    """Declared dimensions plus mandatory ones; mandatory wins on path conflict."""
    by_path = {d.path: d for d in witness.relevant_state.dimensions}
    for dim in mandatory_recurrence_dimensions(witness, before):
        by_path[dim.path] = dim
    return LoopRelevantState(dimensions=list(by_path.values()))
