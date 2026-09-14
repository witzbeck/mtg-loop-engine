"""M5 slices 14–16: mass/self p1p1 from life-gain and ETB (Archangel / Cathars / Heronblade)."""

import pytest

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import (
    SemanticCoverage,
    TriggerEvent,
    VerificationStatus,
)
from mtg_loop_engine.semantics.ir import AddCounterEffect, AddManaEffect, TriggeredAbility
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


@pytest.mark.parametrize(
    "key,event,target",
    [
        ("Archangel of Thune", TriggerEvent.GAIN_LIFE, "each_controlled_creature"),
        ("Cathars' Crusade", TriggerEvent.ENTER_BATTLEFIELD, "each_controlled_creature"),
        ("Heronblade Elite", TriggerEvent.ENTER_BATTLEFIELD, "self"),
    ],
)
def test_counter_cluster_cards_compile_complete(key: str, event: TriggerEvent, target: str):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == event
    )
    effect = next(e for e in trig.effects if isinstance(e, AddCounterEffect))
    assert effect.target == target
    if key == "Heronblade Elite":
        assert trig.filter == "other_controlled_human"
        mana = next(
            e
            for a in report.semantics.abilities
            if getattr(a, "effects", None)
            for e in a.effects
            if isinstance(e, AddManaEffect) and e.equal_to_source_power
        )
        assert mana.equal_to_source_power == "any_color"


def test_heliod_stays_single_target_not_each():
    row = GOLD_ORACLE_FIXTURES["oracle:heliod-sun-crowned"]
    report = compile_oracle_text(
        oracle_id=row.oracle_id,
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.GAIN_LIFE
    )
    effect = trig.effects[0]
    assert isinstance(effect, AddCounterEffect)
    assert effect.target == "target_permanent"


def test_archangel_seed_gain_life_puts_counters_on_each_creature():
    angel = _compile("Archangel of Thune").semantics
    spec = InitialStateSpec(
        permanents=[
            bf("a", angel.oracle_id, angel.name, is_creature=True, power=3, toughness=4),
            bf(
                "b",
                "oracle:buddy",
                "Buddy",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        ]
    )
    buddy = angel.model_copy(
        update={
            "oracle_id": "oracle:buddy",
            "name": "Buddy",
            "types": ["Creature"],
            "abilities": [],
        }
    )
    executor = Executor({angel.oracle_id: angel, "oracle:buddy": buddy})
    state = GameState.from_spec(spec)
    err = executor.run_step(
        state, ActionStep(op="seed_gain_life", actor="a", note="test")
    )
    assert err is None
    assert state.pending_triggers
    ability_id = state.pending_triggers[0]["ability_id"]
    err = executor.run_step(
        state,
        ActionStep(op="resolve_trigger", actor="a", ability_id=ability_id),
    )
    assert err is None
    assert state.permanents["a"].counters.get("p1p1", 0) == 1
    assert state.permanents["b"].counters.get("p1p1", 0) == 1


def test_cathars_etb_puts_counters_on_each_creature():
    crusade = _compile("Cathars' Crusade").semantics
    host = crusade.model_copy(
        update={
            "oracle_id": "oracle:etb-creature",
            "name": "Entrant",
            "types": ["Creature"],
            "abilities": [],
        }
    )
    buddy = crusade.model_copy(
        update={
            "oracle_id": "oracle:buddy",
            "name": "Buddy",
            "types": ["Creature"],
            "abilities": [],
        }
    )
    spec = InitialStateSpec(
        permanents=[
            bf("c", crusade.oracle_id, crusade.name),
            bf("b", "oracle:buddy", "Buddy", is_creature=True, power=1, toughness=1),
            bf(
                "e",
                "oracle:etb-creature",
                "Entrant",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        ]
    )
    executor = Executor(
        {
            crusade.oracle_id: crusade,
            "oracle:buddy": buddy,
            "oracle:etb-creature": host,
        }
    )
    state = GameState.from_spec(spec)
    # Simulate ETB of Entrant after board is up (queue trigger manually via _on_etb).
    executor._on_etb(state, state.permanents["e"])
    assert state.pending_triggers
    ability_id = state.pending_triggers[0]["ability_id"]
    err = executor.run_step(
        state,
        ActionStep(op="resolve_trigger", actor="c", ability_id=ability_id),
    )
    assert err is None
    assert state.permanents["b"].counters.get("p1p1", 0) == 1
    assert state.permanents["e"].counters.get("p1p1", 0) == 1


def test_heronblade_plus_staff_rediscovers():
    heron = _compile("Heronblade Elite").semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(heron, staff, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Heronblade Elite", "Staff of Domination"}


def test_archangel_plus_ballista_rediscovers_with_physics_lifelink_seed():
    angel = _compile("Archangel of Thune").semantics
    # Archangel already has lifelink keyword — product path should not need grant seed.
    ballista_fx = GOLD_ORACLE_FIXTURES["oracle:walking-ballista"]
    ballista = compile_oracle_text(
        oracle_id=ballista_fx.oracle_id,
        name=ballista_fx.name,
        oracle_text=ballista_fx.oracle_text,
        types=ballista_fx.types,
    ).semantics
    found = explore_pair(angel, ballista, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Archangel of Thune", "Walking Ballista"}
