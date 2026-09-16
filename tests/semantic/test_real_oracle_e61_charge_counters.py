"""M5 E61: charge-counter mana and put engines."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaAmount
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


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e61_cards_complete():
    for key in ("Astral Cornucopia", "Druids' Repository", "Coretapper"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_cornucopia_tap_mana_from_charge():
    corn = _compile("Astral Cornucopia").semantics
    ex = Executor({corn.oracle_id: corn})
    state = _state(
        permanents={
            "c": Permanent(
                object_id="c",
                oracle_id=corn.oracle_id,
                name=corn.name,
                is_artifact=True,
                counters={"charge": 3},
            )
        }
    )
    ab = next(a for a in corn.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="c", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.mana.any_color == 3


def test_repository_attacks_then_remove_charge():
    repo = _compile("Druids' Repository").semantics
    attacker = _compile("Coretapper").semantics
    ex = Executor({repo.oracle_id: repo, attacker.oracle_id: attacker})
    state = _state(
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=repo.oracle_id,
                name=repo.name,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=attacker.oracle_id,
                name=attacker.name,
                is_creature=True,
                is_artifact=True,
                power=1,
                toughness=1,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ATTACKS, state.permanents["a"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["r"].counters.get("charge", 0) == 1
    ab = next(
        a
        for a in repo.abilities
        if isinstance(a, ActivatedAbility) and "remove-charge" in a.ability_id
    )
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="r", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.permanents["r"].counters.get("charge", 0) == 0
    assert state.mana.any_color == 1


def test_coretapper_puts_charge_on_artifact():
    tapper = _compile("Coretapper").semantics
    corn = _compile("Astral Cornucopia").semantics
    ex = Executor({tapper.oracle_id: tapper, corn.oracle_id: corn})
    state = _state(
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=tapper.oracle_id,
                name=tapper.name,
                is_creature=True,
                is_artifact=True,
                power=1,
                toughness=1,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=corn.oracle_id,
                name=corn.name,
                is_artifact=True,
            ),
        }
    )
    ab = next(
        a
        for a in tapper.abilities
        if isinstance(a, ActivatedAbility) and "tap-put-charge" in a.ability_id
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="t", ability_id=ab.ability_id, target="c"),
        )
        is None
    )
    assert state.permanents["c"].counters.get("charge", 0) == 1
