"""M5 E15a: attack-trigger remainders (untap lands / damage attacker / draw)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount
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


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e15a_cards_complete():
    for key in ("Bear Umbra", "Caltrops", "Dream Trawler"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_bear_umbra_untaps_lands_on_attack():
    umbra = _compile("Bear Umbra").semantics
    land = CardSemantics(
        oracle_id="oracle:forest",
        name="Forest",
        types=["Basic", "Land", "Forest"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {umbra.oracle_id: umbra, land.oracle_id: land, beater.oracle_id: beater}
    )
    state = _state(
        permanents={
            "u": Permanent(
                object_id="u",
                oracle_id=umbra.oracle_id,
                name=umbra.name,
            ),
            "l": Permanent(
                object_id="l",
                oracle_id=land.oracle_id,
                name="Forest",
                tapped=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ATTACKS, state.permanents["b"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["l"].tapped is False


def test_caltrops_damages_attacker():
    caltrops = _compile("Caltrops").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({caltrops.oracle_id: caltrops, beater.oracle_id: beater})
    state = _state(
        permanents={
            "c": Permanent(
                object_id="c",
                oracle_id=caltrops.oracle_id,
                name=caltrops.name,
                is_artifact=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ATTACKS, state.permanents["b"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["b"].damage_marked == 1


def test_dream_trawler_draws_on_attack():
    dream = _compile("Dream Trawler").semantics
    ex = Executor({dream.oracle_id: dream})
    state = _state(
        permanents={
            "d": Permanent(
                object_id="d",
                oracle_id=dream.oracle_id,
                name=dream.name,
                is_creature=True,
                power=3,
                toughness=5,
            )
        }
    )
    ex._queue_triggers(state, TriggerEvent.ATTACKS, state.permanents["d"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.event_counters.get("draw", 0) == 1
