"""Executor contracts for tap-mana multiplier replacement (M5 slice 11)."""

from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    CardSemantics,
    ManaAmount,
    ManaCost,
    ReplacementMultiplyTapMana,
    SacrificeCost,
    TapCost,
    UntapEffect,
)
from mtg_loop_engine.state.game import GameState


def test_tap_mana_doubles_with_mana_reflection_on_battlefield():
    basalt = CardSemantics(
        oracle_id="oracle:basalt",
        name="Basalt Monolith",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(colorless=3))],
                is_mana_ability=True,
            ),
            ActivatedAbility(
                ability_id="untap",
                costs=[ManaCost(amount=ManaAmount(generic=3))],
                effects=[UntapEffect(target="self")],
            ),
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    reflection = CardSemantics(
        oracle_id="oracle:reflection",
        name="Mana Reflection",
        types=["Enchantment"],
        abilities=[
            ReplacementMultiplyTapMana(
                ability_id="multiply-tap-mana",
                multiplier=2,
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {basalt.oracle_id: basalt, reflection.oracle_id: reflection}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=basalt.oracle_id,
                    name="Basalt Monolith",
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=reflection.oracle_id,
                    name="Mana Reflection",
                ),
            ]
        )
    )
    ex = Executor(semantics)
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="c0", ability_id="tap-mana"),
    )
    assert err is None
    assert state.permanents["c0"].tapped is True
    assert state.mana.colorless == 6


def test_sacrifice_mana_is_not_multiplied():
    outlet = CardSemantics(
        oracle_id="oracle:altar",
        name="Altar",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="sac-mana",
                costs=[SacrificeCost(selector="creature_controlled")],
                effects=[AddManaEffect(amount=ManaAmount(black=1))],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    reflection = CardSemantics(
        oracle_id="oracle:reflection",
        name="Mana Reflection",
        types=["Enchantment"],
        abilities=[
            ReplacementMultiplyTapMana(
                ability_id="multiply-tap-mana",
                multiplier=2,
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    fodder = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {
        outlet.oracle_id: outlet,
        reflection.oracle_id: reflection,
        fodder.oracle_id: fodder,
    }
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=outlet.oracle_id,
                    name="Altar",
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=reflection.oracle_id,
                    name="Mana Reflection",
                ),
                PermanentSpec(
                    object_id="c2",
                    oracle_id=fodder.oracle_id,
                    name="Fodder",
                    is_creature=True,
                    is_token=True,
                ),
            ]
        )
    )
    ex = Executor(semantics)
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="c0",
            ability_id="sac-mana",
            target="c2",
        ),
    )
    assert err is None
    assert state.mana.black == 1
