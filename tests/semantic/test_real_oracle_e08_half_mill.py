"""M5 E08: half-library mill."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import ActivatedAbility, MillEffect, TriggeredAbility
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent
from mtg_loop_engine.semantics.ir import ManaAmount


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


def test_e08_half_mill_cards_complete():
    for key in (
        "Traumatize",
        "Fleet Swallower",
        "Terisian Mindbreaker",
        "Lord Xander, the Collector",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_half_mill_rounded_down():
    traum = _compile("Traumatize").semantics
    ab = next(a for a in traum.abilities if isinstance(a, ActivatedAbility))
    effect = ab.effects[0]
    assert isinstance(effect, MillEffect)
    assert effect.half_library == "down"
    ex = Executor({traum.oracle_id: traum})
    state = GameState(
        permanents={
            "t": Permanent(object_id="t", oracle_id=traum.oracle_id, name=traum.name)
        },
        mana=ManaAmount(),
        library_opponent=53,
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="t", ability_id=ab.ability_id))
        is None
    )
    assert state.library_opponent == 53 - 26
    assert state.event_counters.get("mill", 0) == 26


def test_attacks_half_mill_rounded_up():
    fleet = _compile("Fleet Swallower").semantics
    ab = next(a for a in fleet.abilities if isinstance(a, TriggeredAbility))
    assert ab.event is TriggerEvent.ATTACKS
    assert ab.effects[0].half_library == "up"
    ex = Executor({fleet.oracle_id: fleet})
    state = GameState(
        permanents={
            "f": Permanent(
                object_id="f",
                oracle_id=fleet.oracle_id,
                name=fleet.name,
                is_creature=True,
                power=8,
                toughness=8,
            )
        },
        mana=ManaAmount(),
        library_opponent=53,
    )
    # Manually queue and resolve ATTACKS trigger
    ex._queue_triggers(state, TriggerEvent.ATTACKS, state.permanents["f"])
    assert state.pending_triggers
    assert (
        ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    )
    assert state.library_opponent == 53 - 27


def test_half_mill_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-half-mill",
        name="Fake Half Mill",
        oracle_text="Target player mills half their deck, rounded down.",
        types=["Sorcery"],
        colors=["U"],
        mana_cost=ManaAmount(blue=2, generic=3),
        mana_value=5,
    )
    assert report.semantics.relevant_unsupported()
