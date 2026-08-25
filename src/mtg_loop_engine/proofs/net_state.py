"""Net-state deltas separate from gross event OutputDelta (Wave 0.5).

Gross event counters may rise while the pool is net-zero (e.g. Altar/Gravecrawler).
Do not label ACCUMULATES from event counters alone.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import NetStateDelta
from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.state.game import GameState


def _mana_delta(before: ManaAmount, after: ManaAmount) -> ManaAmount:
    return ManaAmount(
        white=after.white - before.white,
        blue=after.blue - before.blue,
        black=after.black - before.black,
        red=after.red - before.red,
        green=after.green - before.green,
        colorless=after.colorless - before.colorless,
        generic=after.generic - before.generic,
        any_color=after.any_color - before.any_color,
    )


def _creature_token_count(state: GameState) -> int:
    return sum(
        1
        for p in state.permanents.values()
        if p.zone == Zone.BATTLEFIELD and p.is_token and p.is_creature
    )


def _plus_one_counter_total(state: GameState) -> int:
    total = 0
    for p in state.permanents.values():
        if p.zone != Zone.BATTLEFIELD:
            continue
        total += p.counters.get("p1p1", 0) + p.counters.get("+1/+1", 0)
    return total


def derive_net_state(before: GameState, after: GameState) -> NetStateDelta:
    """Pool/life/token/counter deltas across one loop iteration."""
    return NetStateDelta(
        mana=_mana_delta(before.mana, after.mana),
        life_you=after.life_you - before.life_you,
        life_opponent=after.life_opponent - before.life_opponent,
        creature_tokens=_creature_token_count(after) - _creature_token_count(before),
        plus_one_counters=_plus_one_counter_total(after)
        - _plus_one_counter_total(before),
    )


def net_state_matches(actual: NetStateDelta, expected: NetStateDelta) -> list[str]:
    """Return problem strings if actual does not match expected (all fields)."""
    problems: list[str] = []
    for color in (
        "white",
        "blue",
        "black",
        "red",
        "green",
        "colorless",
        "generic",
        "any_color",
    ):
        a = getattr(actual.mana, color)
        e = getattr(expected.mana, color)
        if a != e:
            problems.append(f"net mana.{color}: want {e} got {a}")
    if actual.life_you != expected.life_you:
        problems.append(f"net life_you: want {expected.life_you} got {actual.life_you}")
    if actual.life_opponent != expected.life_opponent:
        problems.append(
            f"net life_opponent: want {expected.life_opponent} got {actual.life_opponent}"
        )
    if actual.creature_tokens != expected.creature_tokens:
        problems.append(
            f"net creature_tokens: want {expected.creature_tokens} got {actual.creature_tokens}"
        )
    if actual.plus_one_counters != expected.plus_one_counters:
        problems.append(
            "net plus_one_counters: "
            f"want {expected.plus_one_counters} got {actual.plus_one_counters}"
        )
    return problems
