"""M5 E50: life / draw replacement effects."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    DealDamageEffect,
    DrawEffect,
    GainLifeEffect,
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
        oracle_id=(
            f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}"
        ),
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e50_cards_complete():
    for key in (
        "Bloodletter of Aclazotz",
        "Alhammarret's Archive",
        "Everlasting Torment",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_bloodletter_doubles_damage_life_loss():
    blood = _compile("Bloodletter of Aclazotz").semantics
    pinger = CardSemantics(
        oracle_id="oracle:pinger",
        name="Pinger",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=2, target="opponent")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({blood.oracle_id: blood, pinger.oracle_id: pinger})
    state = _state(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=blood.oracle_id,
                name=blood.name,
                is_creature=True,
                power=2,
                toughness=4,
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
        life_opponent=40,
    )
    ab = pinger.abilities[0]
    assert isinstance(ab, ActivatedAbility)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="p", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.life_opponent == 36  # 2 damage → 4 life loss


def test_archive_doubles_life_gain_and_draw():
    archive = _compile("Alhammarret's Archive").semantics
    healer = CardSemantics(
        oracle_id="oracle:healer",
        name="Healer",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="heal",
                costs=[TapCost()],
                effects=[GainLifeEffect(amount=3)],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    drawer = CardSemantics(
        oracle_id="oracle:drawer",
        name="Drawer",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="draw",
                costs=[TapCost()],
                effects=[DrawEffect(amount=1)],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {
            archive.oracle_id: archive,
            healer.oracle_id: healer,
            drawer.oracle_id: drawer,
        }
    )
    state = _state(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=archive.oracle_id,
                name=archive.name,
                is_artifact=True,
            ),
            "h": Permanent(
                object_id="h",
                oracle_id=healer.oracle_id,
                name="Healer",
                is_creature=True,
                power=1,
                toughness=1,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=drawer.oracle_id,
                name="Drawer",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        life_you=20,
    )
    heal_ab = healer.abilities[0]
    assert isinstance(heal_ab, ActivatedAbility)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="h", ability_id=heal_ab.ability_id),
        )
        is None
    )
    assert state.life_you == 26
    draw_ab = drawer.abilities[0]
    assert isinstance(draw_ab, ActivatedAbility)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="d", ability_id=draw_ab.ability_id),
        )
        is None
    )
    assert state.event_counters.get("draw", 0) == 2


def test_torment_blocks_life_gain():
    torment = _compile("Everlasting Torment").semantics
    healer = CardSemantics(
        oracle_id="oracle:healer",
        name="Healer",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="heal",
                costs=[TapCost()],
                effects=[GainLifeEffect(amount=5)],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({torment.oracle_id: torment, healer.oracle_id: healer})
    state = _state(
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=torment.oracle_id,
                name=torment.name,
            ),
            "h": Permanent(
                object_id="h",
                oracle_id=healer.oracle_id,
                name="Healer",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        life_you=20,
    )
    ab = healer.abilities[0]
    assert isinstance(ab, ActivatedAbility)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="h", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.life_you == 20
    assert state.event_counters.get("life_gain", 0) == 0
