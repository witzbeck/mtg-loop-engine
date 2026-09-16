"""M5 E67a: artifact untap remainders."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import ActivatedAbility, CardSemantics, ManaAmount
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


def test_e67a_complete():
    for key in ("Filigree Sages", "Corridor Monitor", "Clock of Omens"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_filigree_untaps_artifact():
    sage = _compile("Filigree Sages").semantics
    art = CardSemantics(
        oracle_id="oracle:art",
        name="Gizmo",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({sage.oracle_id: sage, art.oracle_id: art})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=sage.oracle_id,
                name=sage.name,
                is_creature=True,
                is_artifact=True,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=art.oracle_id,
                name="Gizmo",
                is_artifact=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(colorless=2, blue=1),
    )
    ab = next(a for a in sage.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="s", ability_id=ab.ability_id, target="a"),
        )
        is None
    )
    assert state.permanents["a"].tapped is False


def test_clock_taps_two_artifacts():
    clock = _compile("Clock of Omens").semantics
    art = CardSemantics(
        oracle_id="oracle:art",
        name="Gizmo",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({clock.oracle_id: clock, art.oracle_id: art})
    state = GameState(
        permanents={
            "c": Permanent(
                object_id="c",
                oracle_id=clock.oracle_id,
                name=clock.name,
                is_artifact=True,
            ),
            "a1": Permanent(
                object_id="a1",
                oracle_id=art.oracle_id,
                name="Gizmo",
                is_artifact=True,
            ),
            "a2": Permanent(
                object_id="a2",
                oracle_id=art.oracle_id,
                name="Gizmo",
                is_artifact=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in clock.abilities if isinstance(a, ActivatedAbility))
    # Need two untapped: clock + a1, target a2
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="c", ability_id=ab.ability_id, target="a2"),
        )
        is None
    )
    assert state.permanents["a2"].tapped is False
    assert state.permanents["c"].tapped is True
    assert state.permanents["a1"].tapped is True


def test_corridor_etb_untaps():
    mon = _compile("Corridor Monitor").semantics
    art = CardSemantics(
        oracle_id="oracle:art",
        name="Gizmo",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({mon.oracle_id: mon, art.oracle_id: art})
    state = GameState(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=mon.oracle_id,
                name=mon.name,
                is_creature=True,
                is_artifact=True,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=art.oracle_id,
                name="Gizmo",
                is_artifact=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(),
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["m"])
    assert (
        ex.resolve_trigger(state, ActionStep(op="resolve_trigger", target="a"))
        is None
    )
    assert state.permanents["a"].tapped is False


def test_filigree_rejects_nonartifact():
    sage = _compile("Filigree Sages").semantics
    critter = CardSemantics(
        oracle_id="oracle:beast",
        name="Beast",
        types=["Creature", "Beast"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({sage.oracle_id: sage, critter.oracle_id: critter})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=sage.oracle_id,
                name=sage.name,
                is_creature=True,
                is_artifact=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=critter.oracle_id,
                name="Beast",
                is_creature=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(colorless=2, blue=1),
    )
    ab = next(a for a in sage.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="s", ability_id=ab.ability_id, target="b"),
    )
    assert err is not None
