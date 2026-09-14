"""M5 path-a slice 18: South Wind Avatar dies→life=toughness."""

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
from mtg_loop_engine.semantics.ir import GainLifeEffect, TriggeredAbility
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-").replace("'", "")
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_south_wind_compiles_complete():
    report = _compile("South Wind Avatar")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    dies = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.DIES
    )
    assert dies.filter == "other_controlled_creature"
    assert isinstance(dies.effects[0], GainLifeEffect)
    assert dies.effects[0].amount_from_trigger is True
    gain = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.GAIN_LIFE
    )
    assert gain.effects[0].amount == 1


def test_dies_gain_life_uses_subject_toughness():
    wind = _compile("South Wind Avatar").semantics
    buddy = wind.model_copy(
        update={
            "oracle_id": "oracle:buddy",
            "name": "Buddy",
            "types": ["Creature"],
            "abilities": [],
        }
    )
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("w", wind.oracle_id, wind.name, is_creature=True, power=3, toughness=3),
                bf(
                    "b",
                    buddy.oracle_id,
                    buddy.name,
                    is_creature=True,
                    power=2,
                    toughness=5,
                ),
            ],
            life_you=20,
        )
    )
    ex = Executor({wind.oracle_id: wind, buddy.oracle_id: buddy})
    ex.die(state, state.permanents["b"])
    assert state.pending_triggers
    assert state.pending_triggers[0]["amount"] == 5
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="w",
            ability_id=state.pending_triggers[0]["ability_id"],
        ),
    )
    assert err is None
    assert state.life_you == 25


def test_self_death_does_not_fire_other_filter():
    wind = _compile("South Wind Avatar").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("w", wind.oracle_id, wind.name, is_creature=True, power=3, toughness=3),
            ],
            life_you=20,
        )
    )
    ex = Executor({wind.oracle_id: wind})
    ex.die(state, state.permanents["w"])
    assert not any(
        t.get("ability_id", "").startswith("dies-gain")
        or "dies-gain-toughness" in t.get("ability_id", "")
        for t in state.pending_triggers
    )


def test_south_wind_plus_exquisite_discovers():
    wind = _compile("South Wind Avatar").semantics
    blood = _compile("Exquisite Blood").semantics
    found = explore_pair(wind, blood, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"South Wind Avatar", "Exquisite Blood"}
