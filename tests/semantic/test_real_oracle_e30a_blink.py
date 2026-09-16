"""M5 E30a: blink (exile then return) activated / ETB."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
    ManaAmount,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e30a_cards_complete():
    for key in ("Emiel the Blessed", "Eldrazi Displacer", "Felidar Guardian"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_emiel_blink_retriggers_etb():
    emiel = _compile("Emiel the Blessed").semantics
    etb_ping = CardSemantics(
        oracle_id="oracle:etb-ping",
        name="ETB Pinger",
        types=["Creature"],
        abilities=[
            TriggeredAbility(
                ability_id="etb-dmg",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="self",
                effects=[DealDamageEffect(amount=1, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({emiel.oracle_id: emiel, etb_ping.oracle_id: etb_ping})
    state = GameState(
        mana=ManaAmount(colorless=3),
        life_opponent=20,
        permanents={
            "e": Permanent(
                object_id="e",
                oracle_id=emiel.oracle_id,
                name=emiel.name,
                is_creature=True,
                power=4,
                toughness=4,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=etb_ping.oracle_id,
                name="ETB Pinger",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    ab = next(a for a in emiel.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate", actor="e", ability_id=ab.ability_id, target="c"
            ),
        )
        is None
    )
    assert state.permanents["c"].zone == Zone.BATTLEFIELD
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 19


def test_blink_hard_negative_cannot_blink_self():
    emiel = _compile("Emiel the Blessed").semantics
    ex = Executor({emiel.oracle_id: emiel})
    state = GameState(
        mana=ManaAmount(colorless=3),
        permanents={
            "e": Permanent(
                object_id="e",
                oracle_id=emiel.oracle_id,
                name=emiel.name,
                is_creature=True,
                power=4,
                toughness=4,
            ),
        },
    )
    ab = next(a for a in emiel.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="e", ability_id=ab.ability_id, target="e"),
    )
    assert err is not None
