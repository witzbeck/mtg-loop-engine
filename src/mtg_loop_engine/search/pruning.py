"""State fingerprints for bounded search pruning."""

from __future__ import annotations

from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.state.game import GameState


def reusable_fingerprint(state: GameState) -> tuple:
    """Hash reusable board+mana+triggers, ignoring monotonic event counters."""
    perms = tuple(
        sorted(
            (
                p.oracle_id,
                p.zone.value,
                p.tapped,
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
    )
    triggers = tuple(
        (t.get("ability_id"), t.get("source_id")) for t in state.pending_triggers
    )
    return (perms, tokens, mana, triggers)
