"""M5 E02/E03: damage-dealt reflect + token-create ×2."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    CreateTokenEffect,
    DealDamageEffect,
    ManaAmount,
    ManaCost,
    ReplacementDoubleTokens,
    TapCost,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace('/', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e02_reflect_cards_complete():
    for key in (
        "Spitemare",
        "Boros Reckoner",
        "Coalhauler Swine",
        "Brash Taunter",
        "Metropolis Reformer",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )
        ab = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
        assert ab.event.value == "dealt_damage"


def test_e03_token_double_complete():
    for key in ("Parallel Lives", "Anointed Procession"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE
        ab = report.semantics.abilities[0]
        assert isinstance(ab, ReplacementDoubleTokens)
        assert ab.multiplier == 2


def test_dealt_damage_reflect_fires():
    spit = _compile("Spitemare").semantics
    ping_sem = CardSemantics(
        oracle_id="oracle:test-ping",
        name="Test Ping",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=1, target="any_target")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({spit.oracle_id: spit, ping_sem.oracle_id: ping_sem})
    state = GameState(
        permanents={
            "spit": Permanent(
                object_id="spit",
                oracle_id=spit.oracle_id,
                name="Spitemare",
                is_creature=True,
                power=3,
                toughness=3,
            ),
            "ping": Permanent(
                object_id="ping",
                oracle_id=ping_sem.oracle_id,
                name="Test Ping",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="ping", ability_id="ping", target="spit"),
        )
        is None
    )
    assert state.pending_triggers
    while state.pending_triggers:
        err = ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="opponent")
        )
        assert err is None
    assert state.life_opponent == 39
    assert state.permanents["spit"].damage_marked == 1


def test_token_double_multiplies_create():
    lives = _compile("Parallel Lives").semantics
    maker = CardSemantics(
        oracle_id="oracle:token-maker",
        name="Token Maker",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="make",
                costs=[ManaCost(amount=ManaAmount(generic=1))],
                effects=[
                    CreateTokenEffect(name="Squirrel", power=1, toughness=1, quantity=1)
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({lives.oracle_id: lives, maker.oracle_id: maker})
    state = GameState(
        permanents={
            "lives": Permanent(
                object_id="lives",
                oracle_id=lives.oracle_id,
                name="Parallel Lives",
            ),
            "maker": Permanent(
                object_id="maker",
                oracle_id=maker.oracle_id,
                name="Token Maker",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(colorless=1),
    )
    before = sum(1 for p in state.permanents.values() if p.is_token)
    assert (
        ex.activate(state, ActionStep(op="activate", actor="maker", ability_id="make"))
        is None
    )
    after = sum(1 for p in state.permanents.values() if p.is_token)
    assert after - before == 2


def test_token_double_absent_stays_single():
    maker = CardSemantics(
        oracle_id="oracle:token-maker",
        name="Token Maker",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="make",
                costs=[ManaCost(amount=ManaAmount(generic=1))],
                effects=[
                    CreateTokenEffect(name="Squirrel", power=1, toughness=1, quantity=1)
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({maker.oracle_id: maker})
    state = GameState(
        permanents={
            "maker": Permanent(
                object_id="maker",
                oracle_id=maker.oracle_id,
                name="Token Maker",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(colorless=1),
    )
    before = sum(1 for p in state.permanents.values() if p.is_token)
    assert (
        ex.activate(state, ActionStep(op="activate", actor="maker", ability_id="make"))
        is None
    )
    after = sum(1 for p in state.permanents.values() if p.is_token)
    assert after - before == 1
