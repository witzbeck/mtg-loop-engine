"""Basalt + Synthetic Cost Reducer: freeze gross event vs net pool semantics.

OutputDelta today reports gross produced events (mana event counter), not net
mana-pool accumulation. Do not silently redefine OutputDelta to mean net.
Schema/explanation refinement is a separate design decision (ADR follow-up).
"""

from mtg_loop_engine.corpus.gold_core.cases import BASALT, SYNTHETIC_COST_REDUCER
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.enums import Consequence, OutputType, VerificationStatus
from mtg_loop_engine.state.game import GameState


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
