"""M5 slice 40: Shard of the Nightbringer cast intervening-if + half-life drain."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, ManaAmount
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import (
    GainLifeEffect,
    LoseLifeEffect,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-").replace("'", "")
    cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else ManaAmount()
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=cost,
        mana_value=row.mana_value,
    )


def test_shard_compiles_complete_cast_intervening_if():
    report = _compile("Shard of the Nightbringer")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.ENTER_BATTLEFIELD
    )
    assert trig.intervening_if == "cast"
    assert trig.filter == "self"
    assert isinstance(trig.effects[0], LoseLifeEffect)
    assert trig.effects[0].half_life_rounded_up is True
    assert isinstance(trig.effects[1], GainLifeEffect)
    assert trig.effects[1].amount_from_trigger is True


def test_shard_drain_only_when_cast():
    shard = _compile("Shard of the Nightbringer").semantics
    trig = next(
        a
        for a in shard.abilities
        if isinstance(a, TriggeredAbility) and a.intervening_if == "cast"
    )
    # Put onto BF without cast — no trigger.
    spec = InitialStateSpec(
        permanents=[
            bf("s", shard.oracle_id, shard.name, is_creature=True, power=8, toughness=8),
        ],
        life_opponent=40,
        life_you=40,
    )
    ex = Executor({shard.oracle_id: shard})
    state = GameState.from_spec(spec)
    ex._on_etb(state, state.permanents["s"])
    assert not state.pending_triggers

    # Cast from hand — triggers and drains half of 40 = 20.
    spec2 = InitialStateSpec(
        permanents=[
            bf(
                "s",
                shard.oracle_id,
                shard.name,
                is_creature=True,
                power=8,
                toughness=8,
                zone=Zone.HAND,
            ),
        ],
        mana=ManaAmount(black=3, colorless=5),
        life_opponent=40,
        life_you=40,
    )
    state2 = GameState.from_spec(spec2)
    err = ex.run_step(state2, ActionStep(op="cast_from_hand", actor="s"))
    assert err is None
    assert state2.permanents["s"].was_cast is True
    assert state2.pending_triggers
    err = ex.run_step(
        state2,
        ActionStep(op="resolve_trigger", actor="s", ability_id=trig.ability_id),
    )
    assert err is None
    assert state2.life_opponent == 20
    assert state2.life_you == 60


def test_vito_and_bond_still_complete_with_shard():
    """Frontier unlocks: Shard COMPLETE alongside existing Vito / Bond."""
    shard = _compile("Shard of the Nightbringer")
    vito = _compile("Vito, Thorn of the Dusk Rose")
    bond = _compile("Sanguine Bond")
    assert shard.coverage == SemanticCoverage.COMPLETE
    assert vito.coverage == SemanticCoverage.COMPLETE
    assert bond.coverage == SemanticCoverage.COMPLETE
