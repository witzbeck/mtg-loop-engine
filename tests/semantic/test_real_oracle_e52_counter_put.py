"""M5 E52: counter-put trigger payoffs."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    CardSemantics,
    ManaAmount,
    TapCost,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e52_counter_put_cards_complete():
    for key in ("All Will Be One", "Flourishing Defenses"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_all_will_be_one_damages_on_counters():
    awe = _compile("All Will Be One").semantics
    putter = CardSemantics(
        oracle_id="oracle:putter",
        name="Putter",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="put",
                costs=[TapCost()],
                effects=[
                    AddCounterEffect(
                        counter_type="p1p1", quantity=2, target="self"
                    )
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({awe.oracle_id: awe, putter.oracle_id: putter})
    state = GameState(
        permanents={
            "a": Permanent(object_id="a", oracle_id=awe.oracle_id, name=awe.name),
            "p": Permanent(
                object_id="p",
                oracle_id=putter.oracle_id,
                name="Putter",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="p", ability_id="put"))
        is None
    )
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 38


def test_flourishing_creates_on_m1m1():
    flour = _compile("Flourishing Defenses").semantics
    putter = CardSemantics(
        oracle_id="oracle:putter",
        name="Putter",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="put",
                costs=[TapCost()],
                effects=[
                    AddCounterEffect(
                        counter_type="m1m1", quantity=1, target="self"
                    )
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({flour.oracle_id: flour, putter.oracle_id: putter})
    state = GameState(
        permanents={
            "f": Permanent(object_id="f", oracle_id=flour.oracle_id, name=flour.name),
            "p": Permanent(
                object_id="p",
                oracle_id=putter.oracle_id,
                name="Putter",
                is_creature=True,
                power=2,
                toughness=2,
            ),
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="p", ability_id="put"))
        is None
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    elves = [p for p in state.permanents.values() if "Elf" in p.name]
    assert len(elves) == 1


def test_wrong_all_will_wording_partial():
    report = compile_oracle_text(
        oracle_id="oracle:false-awe",
        name="False Awe",
        oracle_text=(
            "Whenever an opponent puts one or more counters on a permanent, "
            "this enchantment deals that much damage to you."
        ),
        types=["Enchantment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
