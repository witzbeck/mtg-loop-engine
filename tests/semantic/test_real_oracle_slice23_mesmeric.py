"""M5 slice 23: Mesmeric Orb untap → mill."""

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
from mtg_loop_engine.semantics.ir import MillEffect, TriggeredAbility
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
        colors=list(row.colors),
    )


def test_mesmeric_compiles_complete():
    report = _compile("Mesmeric Orb")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.UNTAP
    )
    assert isinstance(trig.effects[0], MillEffect)
    assert trig.effects[0].who == "you"


def test_untap_queues_mill_trigger():
    orb = _compile("Mesmeric Orb").semantics
    basalt = _compile("Basalt Monolith Live").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("o", orb.oracle_id, orb.name, is_artifact=True),
                bf("b", basalt.oracle_id, basalt.name, is_artifact=True, tapped=True),
            ]
        )
    )
    ex = Executor({orb.oracle_id: orb, basalt.oracle_id: basalt})
    assert ex._untap_permanent(state, state.permanents["b"])
    assert state.pending_triggers
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="o",
            ability_id=state.pending_triggers[0]["ability_id"],
        ),
    )
    assert err is None
    assert state.event_counters.get("mill", 0) == 1


def test_mesmeric_plus_basalt_discovers():
    orb = _compile("Mesmeric Orb").semantics
    basalt = _compile("Basalt Monolith Live").semantics
    found = explore_pair(orb, basalt, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Mesmeric Orb", "Basalt Monolith"}
