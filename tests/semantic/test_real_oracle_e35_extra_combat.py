"""M5 E35: additional combat (Aggravated Assault, Bloodthirster, Moraug)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaAmount
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e35_cards_complete():
    for key in (
        "Aggravated Assault",
        "Bloodthirster",
        "Moraug, Fury of Akoum",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_aggravated_assault_untaps_and_extra_combat():
    assault = _compile("Aggravated Assault").semantics
    ex = Executor({assault.oracle_id: assault})
    state = GameState(
        mana=ManaAmount(red=2, colorless=3),
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=assault.oracle_id,
                name=assault.name,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id="oracle:creature",
                name="Creature",
                is_creature=True,
                power=2,
                toughness=2,
                tapped=True,
            ),
        },
    )
    ab = next(a for a in assault.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="a", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.permanents["c"].tapped is False
    assert state.event_counters.get("extra_combat", 0) >= 1


def test_extra_combat_hard_negative_insufficient_mana():
    assault = _compile("Aggravated Assault").semantics
    ex = Executor({assault.oracle_id: assault})
    state = GameState(
        mana=ManaAmount(colorless=1),
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=assault.oracle_id,
                name=assault.name,
            ),
        },
    )
    ab = next(a for a in assault.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="a", ability_id=ab.ability_id),
    )
    assert err is not None


def test_moraug_landfall_extra_combat():
    moraug = _compile("Moraug, Fury of Akoum").semantics
    ex = Executor({moraug.oracle_id: moraug})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=moraug.oracle_id,
                name=moraug.name,
                is_creature=True,
                power=6,
                toughness=6,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id="oracle:c",
                name="Creature",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
            "l": Permanent(
                object_id="l",
                oracle_id="oracle:land",
                name="Forest",
                zone=Zone.BATTLEFIELD,
            ),
        },
    )
    ab = next(
        a
        for a in moraug.abilities
        if getattr(a, "event", None) == TriggerEvent.ENTER_BATTLEFIELD
    )
    state.pending_triggers.append(
        {
            "source_id": "m",
            "ability_id": ab.ability_id,
            "subject_id": "l",
        }
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["c"].tapped is False
    assert state.event_counters.get("extra_combat", 0) >= 1
