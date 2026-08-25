"""State fingerprints for bounded search pruning."""

from __future__ import annotations

from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.state.game import GameState


def reusable_fingerprint(state: GameState) -> tuple:
    """Hash reusable board+mana+triggers, ignoring monotonic event counters.

    Equality of reusable fingerprints asserts search-equivalence for all
    currently modeled future legal behavior. States that can diverge in
    activation legality or trigger resolution (summoning sickness, trigger
    subject/amount) must not collapse.
    """
    perms = tuple(
        sorted(
            (
                p.oracle_id,
                p.zone.value,
                p.tapped,
                p.summoning_sick,
                tuple(sorted(p.counters.items())),
                tuple(sorted(p.once_per_turn_used)),
            )
            for p in state.permanents.values()
            if not p.is_token
        )
    )
    tokens = sum(
        1
        for p in state.permanents.values()
        if p.is_token and p.zone == Zone.BATTLEFIELD and p.is_creature
    )
    mana = (
        state.mana.white,
        state.mana.blue,
        state.mana.black,
        state.mana.red,
        state.mana.green,
        state.mana.colorless,
        state.mana.generic,
        state.mana.any_color,
    )
    triggers = tuple(
        (
            t.get("ability_id"),
            t.get("source_id"),
            t.get("subject_id"),
            t.get("amount"),
        )
        for t in state.pending_triggers
    )
    return (perms, tokens, mana, triggers)
