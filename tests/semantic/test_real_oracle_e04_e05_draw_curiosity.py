"""M5 E04/E05: draw-trigger effects + Curiosity auras."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
    DrawEffect,
    ManaAmount,
    TapCost,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e04_draw_trigger_cards_complete():
    for key in (
        "Niv-Mizzet, the Firemind",
        "Psychosis Crawler",
        "Horizon Chimera",
        "Queza, Augur of Agonies",
        "Psychic Corrosion",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )
        ab = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
        assert ab.event is TriggerEvent.DRAW


def test_e05_curiosity_family_complete():
    for key in ("Curiosity", "Keen Sense", "Ophidian Eye"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )
        ab = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
        assert ab.event is TriggerEvent.DAMAGE_OPPONENT


def test_draw_trigger_fires_on_draw_effect():
    niv = _compile("Niv-Mizzet, the Firemind").semantics
    drawer = CardSemantics(
        oracle_id="oracle:drawer",
        name="Drawer",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="draw",
                costs=[TapCost()],
                effects=[DrawEffect(amount=1)],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({niv.oracle_id: niv, drawer.oracle_id: drawer})
    state = GameState(
        permanents={
            "niv": Permanent(
                object_id="niv",
                oracle_id=niv.oracle_id,
                name=niv.name,
                is_creature=True,
                power=4,
                toughness=4,
            ),
            "drawer": Permanent(
                object_id="drawer",
                oracle_id=drawer.oracle_id,
                name="Drawer",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="drawer", ability_id="draw"))
        is None
    )
    assert state.pending_triggers
    while state.pending_triggers:
        err = ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="opponent")
        )
        assert err is None
    assert state.life_opponent == 39


def test_curiosity_draws_on_damage_to_opponent():
    curiosity = _compile("Curiosity").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=1, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({curiosity.oracle_id: curiosity, beater.oracle_id: beater})
    state = GameState(
        permanents={
            "aura": Permanent(
                object_id="aura",
                oracle_id=curiosity.oracle_id,
                name="Curiosity",
            ),
            "beater": Permanent(
                object_id="beater",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="beater", ability_id="ping"))
        is None
    )
    # DAMAGE_OPPONENT → Curiosity draw (+ maybe nested DRAW triggers none)
    draws = 0
    while state.pending_triggers:
        tr = state.pending_triggers[0]
        if "curiosity" in tr["ability_id"] or "draw" in tr["ability_id"]:
            draws += 1
        err = ex.resolve_trigger(state, ActionStep(op="resolve_trigger"))
        assert err is None
    assert state.life_opponent == 39
    assert draws >= 1
    assert state.event_counters.get("draw", 0) >= 1
