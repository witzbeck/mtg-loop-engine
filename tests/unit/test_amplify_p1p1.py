"""Executor contracts for +1/+1 put amplify (M5 slice 12 / Kami)."""

from mtg_loop_engine.proofs.models import InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ReplacementAmplifyP1P1Counters,
)
from mtg_loop_engine.state.game import GameState


def test_kami_amplifies_p1p1_put_by_one():
    kami = CardSemantics(
        oracle_id="oracle:kami",
        name="Kami of Whispered Hopes",
        types=["Creature"],
        abilities=[
            ReplacementAmplifyP1P1Counters(
                ability_id="amplify-p1p1",
                plus=1,
                applies_to="permanents_you_control",
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="kami",
                    oracle_id=kami.oracle_id,
                    name="Kami of Whispered Hopes",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            ]
        )
    )
    source = state.permanents["kami"]
    err = Executor({kami.oracle_id: kami}).apply_effects(
        state,
        source,
        [AddCounterEffect(counter_type="p1p1", quantity=1, target="self")],
        target_id=None,
    )
    assert err is None
    assert source.counters.get("p1p1") == 2


def test_creature_scope_skips_noncreature_permanent():
    scales = CardSemantics(
        oracle_id="oracle:scales",
        name="Hardened Scales",
        types=["Enchantment"],
        abilities=[
            ReplacementAmplifyP1P1Counters(
                ability_id="amplify-p1p1",
                plus=1,
                applies_to="creatures_you_control",
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    artifact = CardSemantics(
        oracle_id="oracle:rock",
        name="Rock",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="scales",
                    oracle_id=scales.oracle_id,
                    name="Hardened Scales",
                ),
                PermanentSpec(
                    object_id="rock",
                    oracle_id=artifact.oracle_id,
                    name="Rock",
                    is_artifact=True,
                ),
            ]
        )
    )
    rock = state.permanents["rock"]
    err = Executor(
        {scales.oracle_id: scales, artifact.oracle_id: artifact}
    ).apply_effects(
        state,
        rock,
        [AddCounterEffect(counter_type="p1p1", quantity=1, target="self")],
        target_id=None,
    )
    assert err is None
    assert rock.counters.get("p1p1") == 1


def test_power_mana_uses_effective_power_with_counters():
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="kami",
                    oracle_id="oracle:kami",
                    name="Kami",
                    is_creature=True,
                    power=1,
                    toughness=1,
                    counters={"p1p1": 3},
                )
            ]
        )
    )
    source = state.permanents["kami"]
    # Tap so tap-mana multiplier path still applies when present.
    source.tapped = True
    err = Executor({}).apply_effects(
        state,
        source,
        [AddManaEffect(equal_to_source_power="any_color")],
        target_id=None,
    )
    assert err is None
    assert state.mana.any_color == 4
