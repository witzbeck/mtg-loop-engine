"""M5 slice 13: Light of Promise / Sunbond life→that-many p1p1 on enchanted host."""

import pytest

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, VerificationStatus
from mtg_loop_engine.semantics.ir import AddCounterEffect, TriggeredAbility
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


@pytest.mark.parametrize("key", ["Light of Promise", "Sunbond"])
def test_life_counter_auras_compile_complete(key: str):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.event == TriggerEvent.GAIN_LIFE
    effect = trig.effects[0]
    assert isinstance(effect, AddCounterEffect)
    assert effect.amount_from_trigger is True
    assert effect.target == "enchanted_creature"


def test_heliod_fixed_counter_does_not_match_that_many_pattern():
    """Adversarial: Heliod puts a fixed counter, not 'that many'."""
    row = GOLD_ORACLE_FIXTURES["oracle:heliod-sun-crowned"]
    report = compile_oracle_text(
        oracle_id=row.oracle_id,
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.GAIN_LIFE
    )
    effect = trig.effects[0]
    assert isinstance(effect, AddCounterEffect)
    assert effect.amount_from_trigger is False
    assert effect.quantity == 1


def test_seed_gain_life_puts_that_many_counters_on_host():
    aura = _compile("Sunbond").semantics
    host_oid = "host"
    aura_oid = "aura"
    spec = InitialStateSpec(
        permanents=[
            bf(
                host_oid,
                "oracle:host-creature",
                "Host",
                is_creature=True,
                power=1,
                toughness=1,
            ),
            bf(aura_oid, aura.oracle_id, aura.name),
        ]
    )
    executor = Executor(
        {
            aura.oracle_id: aura,
            "oracle:host-creature": aura.model_copy(
                update={
                    "oracle_id": "oracle:host-creature",
                    "name": "Host",
                    "types": ["Creature"],
                    "abilities": [],
                }
            ),
        }
    )
    state = GameState.from_spec(spec)
    err = executor.run_step(
        state,
        ActionStep(op="seed_gain_life", actor=aura_oid, note="test"),
    )
    assert err is None
    assert state.pending_triggers
    # Drain-sized seed is 1 by default for GAIN_LIFE without partner sizing.
    amount = state.pending_triggers[0].get("amount")
    assert amount == 1
    err = executor.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor=aura_oid,
            ability_id=state.pending_triggers[0]["ability_id"],
            target=host_oid,
        ),
    )
    assert err is None
    assert state.permanents[host_oid].counters.get("p1p1", 0) == amount
    assert state.permanents[aura_oid].counters.get("p1p1", 0) == 0


def test_sunbond_plus_ballista_rediscovers_with_physics_lifelink_seed():
    sunbond = _compile("Sunbond").semantics
    ballista_fx = GOLD_ORACLE_FIXTURES["oracle:walking-ballista"]
    ballista = compile_oracle_text(
        oracle_id=ballista_fx.oracle_id,
        name=ballista_fx.name,
        oracle_text=ballista_fx.oracle_text,
        types=ballista_fx.types,
    ).semantics
    found = explore_pair(sunbond, ballista, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert found.witness.classification.strict_two_card is True
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Sunbond", "Walking Ballista"}
