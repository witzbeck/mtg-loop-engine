"""Wave 3 physics: SBA lethal damage / 0 toughness, undying return, any_target self-ping.

Claim: Creatures with lethal damage or toughness ≤ 0 die as a state-based action;
undying returns them with +1/+1 iff they had no +1/+1 when they died; remove-counter
pings may target the source creature.
CR: 704.5f (0 toughness), 704.5g (lethal damage), 702.92a/c (undying)
Oracle: (synthetic / keyword model this PR; real Mikaeus/Triskelion deferred)
Engine: Permanent.damage_marked, Executor.apply_state_based_actions, undying seed,
DealDamage any_target via step.target
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
    RemoveCounterEffect,
)
from mtg_loop_engine.state.game import GameState

PINGER_ID = "oracle:synth-pinger"
ABILITY_ID = "counter-ping"


def _pinger_semantics() -> dict[str, CardSemantics]:
    return {
        PINGER_ID: CardSemantics(
            oracle_id=PINGER_ID,
            name="Synth Pinger",
            types=["Creature", "Artifact"],
            abilities=[
                ActivatedAbility(
                    ability_id=ABILITY_ID,
                    costs=[],
                    effects=[
                        RemoveCounterEffect(counter_type="p1p1", quantity=1),
                        DealDamageEffect(amount=1, target="any_target"),
                    ],
                )
            ],
        )
    }


def _board(
    *,
    power: int = 1,
    toughness: int = 1,
    counters: dict[str, int] | None = None,
    undying: bool = False,
) -> tuple[GameState, Executor]:
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_ping",
                    oracle_id=PINGER_ID,
                    name="Synth Pinger",
                    is_creature=True,
                    is_artifact=True,
                    power=power,
                    toughness=toughness,
                    counters=counters or {},
                    undying=undying,
                )
            ]
        )
    )
    return state, Executor(_pinger_semantics())


def test_self_ping_lethal_sba_dies():
    """1/1 with 0 counters after remove → 1 marked damage → SBA dies (704.5g)."""
    state, ex = _board(counters={"p1p1": 1})
    err = ex.run_step(
        state,
        ActionStep(
            op="activate",
            actor="p_ping",
            ability_id=ABILITY_ID,
            target="p_ping",
        ),
    )
    assert err is None
    perm = state.permanents["p_ping"]
    assert perm.zone == Zone.GRAVEYARD
    assert state.event_counters.get("death", 0) == 1


def test_undying_self_ping_returns_with_p1p1():
    """Undying + 0 p1p1 at death → pending return → BF with one p1p1 (702.92a/c)."""
    state, ex = _board(counters={"p1p1": 1}, undying=True)
    err = ex.run_step(
        state,
        ActionStep(
            op="activate",
            actor="p_ping",
            ability_id=ABILITY_ID,
            target="p_ping",
        ),
    )
    assert err is None
    assert state.permanents["p_ping"].zone == Zone.GRAVEYARD
    assert any(
        t["ability_id"] == "__undying_return__" for t in state.pending_triggers
    )
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="p_ping",
            ability_id="__undying_return__",
        ),
    )
    assert err is None
    perm = state.permanents["p_ping"]
    assert perm.zone == Zone.BATTLEFIELD
    assert perm.counters.get("p1p1", 0) == 1
    assert perm.damage_marked == 0
    assert perm.summoning_sick is True
    assert perm.tapped is False


def test_undying_does_not_return_with_p1p1_at_death():
    """Hard negative: undying does not fire when the creature had ≥1 p1p1 (702.92c)."""
    # 2/2 with 1 counter: remove leaves 2/2 0 counters; sacrifice to die with 0? 
    # Spec: dies with 1 p1p1 and undying → no return. Sacrifice while still holding counter.
    state, ex = _board(power=2, toughness=2, counters={"p1p1": 1}, undying=True)
    perm = state.permanents["p_ping"]
    assert perm.counters.get("p1p1", 0) == 1
    ex.die(state, perm)
    assert perm.zone == Zone.GRAVEYARD
    assert not any(
        t["ability_id"] == "__undying_return__" for t in state.pending_triggers
    )


def test_any_target_opponent_ping_preserves_life_damage():
    """any_target + target=opponent → life_opponent (Heliod/Ballista path)."""
    state, ex = _board(counters={"p1p1": 1})
    before = state.life_opponent
    err = ex.run_step(
        state,
        ActionStep(
            op="activate",
            actor="p_ping",
            ability_id=ABILITY_ID,
            target="opponent",
        ),
    )
    assert err is None
    assert state.life_opponent == before - 1
    assert state.permanents["p_ping"].zone == Zone.BATTLEFIELD
    assert state.event_counters.get("damage", 0) == 1


def test_remove_counter_zero_toughness_sba():
    """0/0 with last p1p1 removed → effective toughness ≤ 0 → SBA dies (704.5f)."""
    state, ex = _board(power=0, toughness=0, counters={"p1p1": 1})
    err = ex.run_step(
        state,
        ActionStep(
            op="activate",
            actor="p_ping",
            ability_id=ABILITY_ID,
            target="opponent",
        ),
    )
    assert err is None
    assert state.life_opponent == 39
    assert state.permanents["p_ping"].zone == Zone.GRAVEYARD


def test_seed_grant_undying():
    state, ex = _board(counters={"p1p1": 1})
    assert state.permanents["p_ping"].undying is False
    err = ex.run_step(
        state,
        ActionStep(
            op="seed_grant_undying",
            target="p_ping",
            note="Mikaeus-class undying grant seed",
        ),
    )
    assert err is None
    assert state.permanents["p_ping"].undying is True
