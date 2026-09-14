"""M5 slices 19–20: ETB bounce controlled creature (Shrieking Drake / Whitemane Lion)."""

import pytest

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import (
    SemanticCoverage,
    TriggerEvent,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.ir import MoveToZoneEffect, TriggeredAbility
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
    )


@pytest.mark.parametrize("key", ["Shrieking Drake", "Whitemane Lion"])
def test_etb_bounce_cards_compile_complete(key: str):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.ENTER_BATTLEFIELD
    )
    effect = trig.effects[0]
    assert isinstance(effect, MoveToZoneEffect)
    assert effect.zone == Zone.HAND
    assert effect.target == "controlled_creature"


def test_etb_bounce_returns_controlled_creature_to_hand():
    drake = _compile("Shrieking Drake").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf(
                    "d",
                    drake.oracle_id,
                    drake.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        )
    )
    ex = Executor({drake.oracle_id: drake})
    ex._on_etb(state, state.permanents["d"])
    assert state.pending_triggers
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="d",
            ability_id=state.pending_triggers[0]["ability_id"],
            target="d",
        ),
    )
    assert err is None
    assert state.permanents["d"].zone == Zone.HAND


def test_etb_bounce_rejects_non_creature_target():
    drake = _compile("Shrieking Drake").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("d", drake.oracle_id, drake.name, is_creature=True),
                bf("a", alarm.oracle_id, alarm.name, is_creature=False),
            ]
        )
    )
    ex = Executor({drake.oracle_id: drake, alarm.oracle_id: alarm})
    ex._on_etb(state, state.permanents["d"])
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="d",
            ability_id=state.pending_triggers[0]["ability_id"],
            target="a",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET
