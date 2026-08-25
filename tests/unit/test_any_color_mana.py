"""Any-color mana pays colored costs (Phyrexian Altar class)."""

from mtg_loop_engine.proofs.models import InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.semantics.ir import ManaAmount
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
