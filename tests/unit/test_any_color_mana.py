"""Any-color mana pays colored costs (Phyrexian Altar class)."""

from mtg_loop_engine.proofs.models import InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.semantics.ir import AddManaEffect, ManaAmount
from mtg_loop_engine.state.game import GameState


def test_any_color_pays_black_cost():
    state = GameState.from_spec(InitialStateSpec(mana=ManaAmount(any_color=1)))
    err = Executor({}).pay_mana(state, ManaAmount(black=1))
    assert err is None
    assert state.mana.any_color == 0


def test_generic_cannot_pay_black_cost():
    state = GameState.from_spec(InitialStateSpec(mana=ManaAmount(generic=1)))
    err = Executor({}).pay_mana(state, ManaAmount(black=1))
    assert err is not None
    assert err.status == VerificationStatus.MANA_RESTRICTION


def test_add_mana_equal_to_source_power():
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="joiner",
                    oracle_id="oracle:joiner",
                    name="Viridian Joiner",
                    is_creature=True,
                    power=3,
                    toughness=1,
                )
            ]
        )
    )
    source = state.permanents["joiner"]
    err = Executor({}).apply_effects(
        state,
        source,
        [AddManaEffect(equal_to_source_power="green")],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 3


def test_add_mana_equal_to_source_power_any_color():
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="kami",
                    oracle_id="oracle:kami",
                    name="Kami",
                    is_creature=True,
                    power=2,
                    toughness=2,
                )
            ]
        )
    )
    source = state.permanents["kami"]
    err = Executor({}).apply_effects(
        state,
        source,
        [AddManaEffect(equal_to_source_power="any_color")],
        target_id=None,
    )
    assert err is None
    assert state.mana.any_color == 2
