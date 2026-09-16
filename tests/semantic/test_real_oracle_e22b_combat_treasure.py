"""M5 E22b: combat/dealt damage → Treasure tokens."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
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


def test_e22b_treasure_cards_complete():
    for key in ("Old Gnawbone", "Grim Hireling", "Smaug the Impenetrable"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_gnawbone_creates_that_many_treasures():
    gnaw = _compile("Old Gnawbone").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=3, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({gnaw.oracle_id: gnaw, beater.oracle_id: beater})
    state = GameState(
        permanents={
            "g": Permanent(
                object_id="g",
                oracle_id=gnaw.oracle_id,
                name=gnaw.name,
                is_creature=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="b", ability_id="ping", target="opponent")
        )
        is None
    )
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    treasures = [p for p in state.permanents.values() if p.name == "Treasure"]
    assert len(treasures) == 3


def test_smaug_dealt_damage_treasures():
    smaug = _compile("Smaug the Impenetrable").semantics
    ping = CardSemantics(
        oracle_id="oracle:ping",
        name="Ping",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="hit",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=2, target="any_target")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({smaug.oracle_id: smaug, ping.oracle_id: ping})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=smaug.oracle_id,
                name=smaug.name,
                is_creature=True,
                power=5,
                toughness=5,
            ),
            "p": Permanent(
                object_id="p",
                oracle_id=ping.oracle_id,
                name="Ping",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="p", ability_id="hit", target="s")
        )
        is None
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert sum(1 for p in state.permanents.values() if p.name == "Treasure") == 2


def test_copy_treasure_wording_stays_partial():
    report = compile_oracle_text(
        oracle_id="oracle:false-treasure",
        name="False Treasure",
        oracle_text=(
            "Whenever a creature you control deals combat damage to a player, "
            "create a token that's a copy of target Treasure."
        ),
        types=["Enchantment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
