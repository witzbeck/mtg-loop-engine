"""M5 slice 21: Ivy Lane Denizen green ETB → target p1p1."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import AddCounterEffect, TriggeredAbility
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-")
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
    )


def test_ivy_lane_compiles_complete():
    report = _compile("Ivy Lane Denizen")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    assert report.semantics.colors == ["G"]
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.ENTER_BATTLEFIELD
    )
    assert trig.filter == "other_controlled_green"
    effect = trig.effects[0]
    assert isinstance(effect, AddCounterEffect)
    assert effect.target == "target_permanent"


def test_green_etb_puts_counter_on_target():
    ivy = _compile("Ivy Lane Denizen").semantics
    green = ivy.model_copy(
        update={
            "oracle_id": "oracle:green-buddy",
            "name": "Green Buddy",
            "types": ["Creature", "Elf"],
            "colors": ["G"],
            "abilities": [],
        }
    )
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf(
                    "ivy",
                    ivy.oracle_id,
                    ivy.name,
                    is_creature=True,
                    colors=["G"],
                    power=2,
                    toughness=3,
                ),
                bf(
                    "g",
                    green.oracle_id,
                    green.name,
                    is_creature=True,
                    colors=["G"],
                    power=1,
                    toughness=1,
                ),
            ]
        )
    )
    ex = Executor({ivy.oracle_id: ivy, green.oracle_id: green})
    ex._on_etb(state, state.permanents["g"])
    assert state.pending_triggers
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="ivy",
            ability_id=state.pending_triggers[0]["ability_id"],
            target="g",
        ),
    )
    assert err is None
    assert state.permanents["g"].counters.get("p1p1", 0) == 1


def test_non_green_etb_does_not_fire():
    ivy = _compile("Ivy Lane Denizen").semantics
    red = ivy.model_copy(
        update={
            "oracle_id": "oracle:red-buddy",
            "name": "Red Buddy",
            "types": ["Creature"],
            "colors": ["R"],
            "abilities": [],
        }
    )
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("ivy", ivy.oracle_id, ivy.name, is_creature=True, colors=["G"]),
                bf("r", red.oracle_id, red.name, is_creature=True, colors=["R"]),
            ]
        )
    )
    ex = Executor({ivy.oracle_id: ivy, red.oracle_id: red})
    ex._on_etb(state, state.permanents["r"])
    assert not any(
        "etb-green" in t.get("ability_id", "") for t in state.pending_triggers
    )
