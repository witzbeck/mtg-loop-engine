"""Basalt + Synthetic Cost Reducer: freeze gross event vs net pool semantics.

OutputDelta reports gross produced events (mana event counter), not net
mana-pool accumulation. NetStateDelta reports pool benefit separately.
"""

from mtg_loop_engine.corpus.gold_core.cases import BASALT, SYNTHETIC_COST_REDUCER
from mtg_loop_engine.proofs.models import NetStateDelta
from mtg_loop_engine.proofs.net_state import derive_net_state
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.enums import Consequence, OutputType, VerificationStatus
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import Verifier


def test_basalt_grounds_gross_mana_vs_net_pool():
    found = explore_pair(BASALT, SYNTHETIC_COST_REDUCER)
    assert found is not None
    witness, proof = found.witness, found.proof
    assert proof.status == VerificationStatus.VERIFIED

    mana_out = next(o for o in proof.output_deltas if o.type == OutputType.MANA)
    untap_out = next(o for o in proof.output_deltas if o.type == OutputType.UNTAP)
    # Gross event production (current OutputDelta contract).
    assert mana_out.delta_per_iteration == 3
    assert mana_out.consequence == Consequence.ACCUMULATES
    assert untap_out.delta_per_iteration == 1

    executor = Executor({c.oracle_id: c for c in witness.card_semantics})
    state = GameState.from_spec(witness.initial_state)
    assert executor.run_sequence(state, witness.setup_actions) is None
    before = state.copy()
    assert executor.run_sequence(state, witness.loop_actions) is None

    # Untap cost after Synthetic Cost Reducer is {2}; produce {C}{C}{C}.
    assert state.event_counters.get("mana", 0) - before.event_counters.get("mana", 0) == 3
    net_colorless = state.mana.colorless - before.mana.colorless
    assert net_colorless == 1
    # Spent = produced − net (characterization of today's physics).
    assert 3 - net_colorless == 2

    net = derive_net_state(before, state)
    assert net.mana.colorless == 1
    assert proof.net_state is not None
    assert proof.net_state.mana.colorless == 1


def test_expected_net_state_gate_rejects_mismatch():
    found = explore_pair(BASALT, SYNTHETIC_COST_REDUCER)
    assert found is not None
    bad = found.witness.model_copy(
        update={
            "expected_net_state": NetStateDelta(mana=ManaAmount(colorless=99)),
        }
    )
    proof = Verifier().verify(bad)
    assert proof.status == VerificationStatus.NOT_A_LOOP
    assert proof.rejection_reason and "net mana.colorless" in proof.rejection_reason
