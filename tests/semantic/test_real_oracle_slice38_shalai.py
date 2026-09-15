"""M5 slice 38: Shalai and Hallar COUNTER_ADDED → that-much damage."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    DealDamageEffect,
    ManaAmount,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-").replace("'", "")
    cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else ManaAmount()
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=cost,
        mana_value=row.mana_value,
    )


def test_shalai_compiles_complete_counter_damage():
    report = _compile("Shalai and Hallar")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.COUNTER_ADDED
    )
    assert trig.filter == "controlled_creature"
    effect = trig.effects[0]
    assert isinstance(effect, DealDamageEffect)
    assert effect.amount_from_trigger is True
    assert effect.target == "opponent"


def test_shalai_deals_that_much_when_counters_put():
    shalai = _compile("Shalai and Hallar").semantics
    buddy = shalai.model_copy(
        update={
            "oracle_id": "oracle:buddy",
            "name": "Buddy",
            "types": ["Creature"],
            "abilities": [],
        }
    )
    putter = shalai.model_copy(
        update={
            "oracle_id": "oracle:putter",
            "name": "Putter",
            "types": ["Creature"],
            "abilities": [
                ActivatedAbility(
                    ability_id="put-p1p1",
                    costs=[],
                    effects=[
                        AddCounterEffect(
                            counter_type="p1p1", quantity=3, target="target_permanent"
                        )
                    ],
                )
            ],
        }
    )
    spec = InitialStateSpec(
        permanents=[
            bf("s", shalai.oracle_id, shalai.name, is_creature=True, power=3, toughness=3),
            bf("b", "oracle:buddy", "Buddy", is_creature=True, power=1, toughness=1),
            bf("p", "oracle:putter", "Putter", is_creature=True, power=1, toughness=1),
        ]
    )
    ex = Executor(
        {shalai.oracle_id: shalai, "oracle:buddy": buddy, "oracle:putter": putter}
    )
    state = GameState.from_spec(spec)
    life_before = state.life_opponent
    err = ex.run_step(
        state, ActionStep(op="activate", actor="p", ability_id="put-p1p1", target="b")
    )
    assert err is None
    assert state.pending_triggers
    shalai_trig = next(t for t in state.pending_triggers if t["source_id"] == "s")
    err = ex.run_step(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="s",
            ability_id=shalai_trig["ability_id"],
        ),
    )
    assert err is None
    assert state.life_opponent == life_before - 3


def test_shalai_plus_heliod_rediscovers():
    shalai = _compile("Shalai and Hallar").semantics
    heliod_fx = GOLD_ORACLE_FIXTURES["oracle:heliod-sun-crowned"]
    heliod = compile_oracle_text(
        oracle_id=heliod_fx.oracle_id,
        name=heliod_fx.name,
        oracle_text=heliod_fx.oracle_text,
        types=heliod_fx.types,
    ).semantics
    found = explore_pair(shalai, heliod, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Shalai and Hallar", "Heliod, Sun-Crowned"}


def test_shalai_plus_archangel_both_compile_complete():
    """Archangel mass-puts explode the trigger queue; explorer has no short close.

    Frontier still unlocks the Spellbook pair once both cards are COMPLETE.
    """
    shalai = _compile("Shalai and Hallar")
    angel = _compile("Archangel of Thune")
    assert shalai.coverage == SemanticCoverage.COMPLETE
    assert angel.coverage == SemanticCoverage.COMPLETE
