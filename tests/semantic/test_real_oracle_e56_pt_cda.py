"""M5 E56: characteristic-defining */* and Ashaya Forests."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
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


def test_e56_cards_complete():
    for key in (
        "Ashaya, Soul of the Wild",
        "Psychosis Crawler",
        "Soul of Eternity",
        "Renata, Called to the Hunt",
        "Body of Knowledge",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_ashaya_forests_count_as_lands_for_cda():
    ashaya = _compile("Ashaya, Soul of the Wild").semantics
    creature = CardSemantics(
        oracle_id="oracle:bear",
        name="Bear",
        types=["Creature"],
        coverage=SemanticCoverage.COMPLETE,
    )
    forest = CardSemantics(
        oracle_id="oracle:forest",
        name="Forest",
        types=["Basic", "Land", "Forest"],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {
            ashaya.oracle_id: ashaya,
            creature.oracle_id: creature,
            forest.oracle_id: forest,
        }
    )
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=ashaya.oracle_id,
                name=ashaya.name,
                is_creature=True,
                power=0,
                toughness=0,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=creature.oracle_id,
                name="Bear",
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "l": Permanent(
                object_id="l",
                oracle_id=forest.oracle_id,
                name="Forest",
                zone=Zone.BATTLEFIELD,
            ),
        }
    )
    # Ashaya + Bear (Forest via Ashaya) + Forest land = 3 lands for CDA.
    assert ex._effective_power(state, state.permanents["a"]) == 3
    assert ex._is_land_permanent(state.permanents["b"], state)


def test_ashaya_tokens_are_not_forests():
    ashaya = _compile("Ashaya, Soul of the Wild").semantics
    token = CardSemantics(
        oracle_id="oracle:token",
        name="Soldier",
        types=["Creature"],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({ashaya.oracle_id: ashaya, token.oracle_id: token})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=ashaya.oracle_id,
                name=ashaya.name,
                is_creature=True,
            ),
            "t": Permanent(
                object_id="t",
                oracle_id=token.oracle_id,
                name="Soldier",
                is_creature=True,
                is_token=True,
            ),
        }
    )
    assert not ex._is_land_permanent(state.permanents["t"], state)


def test_body_dealt_damage_draws():
    body = _compile("Body of Knowledge").semantics
    pinger = CardSemantics(
        oracle_id="oracle:ping",
        name="Pinger",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=2, target="any_target")],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({body.oracle_id: body, pinger.oracle_id: pinger})
    state = GameState(
        mana=ManaAmount(),
        hand_you=3,
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=body.oracle_id,
                name=body.name,
                is_creature=True,
                power=0,
                toughness=0,
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
    ab = pinger.abilities[0]
    assert isinstance(ab, ActivatedAbility)
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate",
                actor="p",
                ability_id=ab.ability_id,
                target="b",
            ),
        )
        is None
    )
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.hand_you == 5
