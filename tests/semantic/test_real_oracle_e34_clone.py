"""M5 E34: enter-as-copy (Clone, Mirror Image, Sculpting Steel)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import ManaAmount
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


def test_e34_cards_complete():
    for key in ("Clone", "Mirror Image", "Sculpting Steel"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_clone_becomes_copy_of_target():
    clone = _compile("Clone").semantics
    ex = Executor({clone.oracle_id: clone})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "cl": Permanent(
                object_id="cl",
                oracle_id=clone.oracle_id,
                name=clone.name,
                is_creature=True,
                power=0,
                toughness=0,
            ),
            "t": Permanent(
                object_id="t",
                oracle_id="oracle:bear",
                name="Grizzly Bears",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        },
    )
    ab = next(
        a
        for a in clone.abilities
        if getattr(a, "event", None) == TriggerEvent.ENTER_BATTLEFIELD
    )
    state.pending_triggers.append(
        {"source_id": "cl", "ability_id": ab.ability_id, "subject_id": "cl"}
    )
    assert (
        ex.resolve_trigger(
            state,
            ActionStep(op="resolve_trigger", target="t"),
        )
        is None
    )
    assert state.permanents["cl"].name == "Grizzly Bears"
    assert state.permanents["cl"].power == 2
    assert state.event_counters.get("become_copy", 0) >= 1


def test_clone_hard_negative_self():
    clone = _compile("Clone").semantics
    ex = Executor({clone.oracle_id: clone})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "cl": Permanent(
                object_id="cl",
                oracle_id=clone.oracle_id,
                name=clone.name,
                is_creature=True,
                power=0,
                toughness=0,
            ),
        },
    )
    ab = next(
        a
        for a in clone.abilities
        if getattr(a, "event", None) == TriggerEvent.ENTER_BATTLEFIELD
    )
    state.pending_triggers.append(
        {"source_id": "cl", "ability_id": ab.ability_id, "subject_id": "cl"}
    )
    err = ex.resolve_trigger(
        state,
        ActionStep(op="resolve_trigger", target="cl"),
    )
    assert err is not None
