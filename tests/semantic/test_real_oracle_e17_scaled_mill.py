"""M5 E17: scaled mill + Bruvac double mill."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    ManaAmount,
    MillEffect,
    ReplacementDoubleMill,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e17_scaled_mill_complete():
    for key in ("Mindcrank Scaled", "Keening Stone", "Bruvac the Grandiloquent"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_mindcrank_mills_that_many():
    mind = _compile("Mindcrank Scaled").semantics
    ab = next(a for a in mind.abilities if isinstance(a, TriggeredAbility))
    assert ab.effects[0].amount_from_trigger
    ex = Executor({mind.oracle_id: mind})
    state = GameState(
        permanents={
            "m": Permanent(
                object_id="m", oracle_id=mind.oracle_id, name=mind.name, is_artifact=True
            )
        },
        mana=ManaAmount(),
        library_opponent=60,
    )
    ex._queue_triggers(
        state, TriggerEvent.OPPONENT_LOSE_LIFE, state.permanents["m"], amount=5
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.library_opponent == 55
    assert state.graveyard_opponent == 5


def test_keening_mills_graveyard_count():
    stone = _compile("Keening Stone").semantics
    ab = next(a for a in stone.abilities if isinstance(a, ActivatedAbility))
    ex = Executor({stone.oracle_id: stone})
    state = GameState(
        permanents={
            "k": Permanent(
                object_id="k",
                oracle_id=stone.oracle_id,
                name=stone.name,
                is_artifact=True,
                summoning_sick=False,
            )
        },
        mana=ManaAmount(colorless=5),
        library_opponent=60,
        graveyard_opponent=7,
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="k", ability_id=ab.ability_id))
        is None
    )
    assert state.library_opponent == 53
    assert state.graveyard_opponent == 14


def test_bruvac_doubles_mill():
    bruvac = _compile("Bruvac the Grandiloquent").semantics
    assert any(isinstance(a, ReplacementDoubleMill) for a in bruvac.abilities)
    mind = _compile("Mindcrank Scaled").semantics
    ex = Executor({bruvac.oracle_id: bruvac, mind.oracle_id: mind})
    state = GameState(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=bruvac.oracle_id,
                name=bruvac.name,
                is_creature=True,
            ),
            "m": Permanent(
                object_id="m", oracle_id=mind.oracle_id, name=mind.name, is_artifact=True
            ),
        },
        mana=ManaAmount(),
        library_opponent=60,
    )
    ex._queue_triggers(
        state, TriggerEvent.OPPONENT_LOSE_LIFE, state.permanents["m"], amount=3
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.library_opponent == 54  # 3 * 2


def test_scaled_mill_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-mill",
        name="Fake Mill",
        oracle_text="{5}, {T}: Target player mills X cards, where X is their life total.",
        types=["Artifact"],
        mana_cost=ManaAmount(generic=6),
        mana_value=6,
    )
    assert report.semantics.relevant_unsupported()
