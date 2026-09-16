"""M5 E22a: Eldrazi token creates, Exalted double-tokens, Ajani's Chosen."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    CreateTokenEffect,
    ManaAmount,
    ReplacementDoubleTokens,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e22a_eldrazi_and_chosen_complete():
    for key in (
        "Brood Monitor",
        "Emrakul's Hatcher",
        "Spawnsire of Ulamog",
        "Exalted Sunborn",
        "Ajani's Chosen",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_exalted_sunborn_doubles_tokens():
    report = _compile("Exalted Sunborn")
    assert any(
        isinstance(a, ReplacementDoubleTokens) for a in report.semantics.abilities
    )


def test_brood_monitor_creates_three_scions():
    brood = _compile("Brood Monitor").semantics
    ex = Executor({brood.oracle_id: brood})
    state = GameState(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=brood.oracle_id,
                name=brood.name,
                is_creature=True,
            )
        },
        mana=ManaAmount(),
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["b"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    tokens = [p for p in state.permanents.values() if p.is_token]
    assert len(tokens) == 3
    assert all(t.name == "Eldrazi Scion" for t in tokens)


def test_spawnsire_creates_two_spawn():
    spawn = _compile("Spawnsire of Ulamog").semantics
    ex = Executor({spawn.oracle_id: spawn})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=spawn.oracle_id,
                name=spawn.name,
                is_creature=True,
            )
        },
        mana=ManaAmount(colorless=4),
    )
    ab = next(a for a in spawn.abilities if isinstance(a, ActivatedAbility))
    assert isinstance(ab.effects[0], CreateTokenEffect)
    assert ab.effects[0].quantity == 2
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="s", ability_id=ab.ability_id)
        )
        is None
    )
    assert sum(1 for p in state.permanents.values() if p.is_token) == 2


def test_ajanis_chosen_makes_cat_on_enchantment_etb():
    chosen = _compile("Ajani's Chosen").semantics
    aura = CardSemantics(
        oracle_id="oracle:aura",
        name="Test Aura",
        types=["Enchantment", "Aura"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({chosen.oracle_id: chosen, aura.oracle_id: aura})
    state = GameState(
        permanents={
            "c": Permanent(
                object_id="c",
                oracle_id=chosen.oracle_id,
                name=chosen.name,
                is_creature=True,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=aura.oracle_id,
                name="Test Aura",
            ),
        },
        mana=ManaAmount(),
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["a"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    cats = [p for p in state.permanents.values() if p.is_token and p.name == "Cat"]
    assert len(cats) == 1
    assert cats[0].power == 2 and cats[0].toughness == 2


def test_wrong_eldrazi_create_stays_partial():
    report = compile_oracle_text(
        oracle_id="oracle:false-eldrazi",
        name="False Eldrazi",
        oracle_text=(
            "When this creature enters, create three tokens that are copies of "
            "target Eldrazi."
        ),
        types=["Creature"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()
