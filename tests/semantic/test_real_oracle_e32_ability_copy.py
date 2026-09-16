"""M5 E32: ability / trigger copy (Rings / Bracers / Strionic)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
    ManaAmount,
    ManaCost,
    StaticCopyActivatedAbility,
    TriggeredAbility,
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


def test_e32_cards_complete():
    for key in (
        "Rings of Brighthearth",
        "Illusionist's Bracers",
        "Strionic Resonator",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_rings_copies_non_mana_activation():
    rings = _compile("Rings of Brighthearth").semantics
    assert any(isinstance(a, StaticCopyActivatedAbility) for a in rings.abilities)
    pinger = CardSemantics(
        oracle_id="oracle:pinger",
        name="Pinger",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[ManaCost(amount=ManaAmount(generic=1))],
                effects=[DealDamageEffect(amount=1, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({rings.oracle_id: rings, pinger.oracle_id: pinger})
    state = GameState(
        mana=ManaAmount(colorless=3),
        life_opponent=20,
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=rings.oracle_id,
                name=rings.name,
                is_artifact=True,
            ),
            "p": Permanent(
                object_id="p",
                oracle_id=pinger.oracle_id,
                name="Pinger",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="p", ability_id="ping"),
        )
        is None
    )
    assert state.life_opponent == 18
    assert state.event_counters.get("ability_copy", 0) >= 1


def test_rings_hard_negative_skips_mana_abilities():
    rings = _compile("Rings of Brighthearth").semantics
    basalt = _compile("Basalt Monolith Live").semantics
    ex = Executor({rings.oracle_id: rings, basalt.oracle_id: basalt})
    mana_ab = next(
        a
        for a in basalt.abilities
        if isinstance(a, ActivatedAbility) and a.is_mana_ability
    )
    state = GameState(
        mana=ManaAmount(colorless=10),
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=rings.oracle_id,
                name=rings.name,
                is_artifact=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=basalt.oracle_id,
                name=basalt.name,
                is_artifact=True,
            ),
        },
    )
    before = state.mana.colorless
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="b", ability_id=mana_ab.ability_id),
        )
        is None
    )
    # Mana ability adds 3; Rings must not double it.
    assert state.mana.colorless == before + 3
    assert state.event_counters.get("ability_copy", 0) == 0


def test_bracers_free_copy_creature_activation():
    bracers = _compile("Illusionist's Bracers").semantics
    pinger = CardSemantics(
        oracle_id="oracle:creeping-ping",
        name="Creeping Ping",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-ping",
                costs=[],
                effects=[DealDamageEffect(amount=1, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({bracers.oracle_id: bracers, pinger.oracle_id: pinger})
    state = GameState(
        mana=ManaAmount(),
        life_opponent=20,
        permanents={
            "eq": Permanent(
                object_id="eq",
                oracle_id=bracers.oracle_id,
                name=bracers.name,
                is_artifact=True,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=pinger.oracle_id,
                name="Creeping Ping",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="c", ability_id="tap-ping"),
        )
        is None
    )
    assert state.life_opponent == 18


def test_strionic_copies_pending_trigger():
    strionic = _compile("Strionic Resonator").semantics
    etb = CardSemantics(
        oracle_id="oracle:etb-ping",
        name="ETB Ping",
        types=["Creature"],
        abilities=[
            TriggeredAbility(
                ability_id="etb-dmg",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="self",
                effects=[DealDamageEffect(amount=1, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({strionic.oracle_id: strionic, etb.oracle_id: etb})
    state = GameState(
        mana=ManaAmount(colorless=2),
        life_opponent=20,
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=strionic.oracle_id,
                name=strionic.name,
                is_artifact=True,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=etb.oracle_id,
                name="ETB Ping",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    # Seed a pending trigger as if ETB just fired.
    state.pending_triggers.append(
        {
            "source_id": "c",
            "ability_id": "etb-dmg",
            "subject_id": "c",
        }
    )
    ab = next(a for a in strionic.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="s", ability_id=ab.ability_id),
        )
        is None
    )
    assert len(state.pending_triggers) == 2
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 18
