"""M5 E53: Adapt N + p1p1-put payoffs."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaAmount
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


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e53_cards_complete():
    for key in ("Basking Broodscale", "Benthic Biomancer", "Incubation Druid"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_adapt_puts_when_none_then_noop():
    druid = _compile("Incubation Druid").semantics
    ex = Executor({druid.oracle_id: druid})
    state = _state(
        permanents={
            "d": Permanent(
                object_id="d",
                oracle_id=druid.oracle_id,
                name=druid.name,
                is_creature=True,
                power=0,
                toughness=2,
            )
        },
        mana=ManaAmount(colorless=3, green=2),
    )
    ab = next(a for a in druid.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="d", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.permanents["d"].counters.get("p1p1", 0) == 3
    state.mana = ManaAmount(colorless=3, green=2)
    state.permanents["d"].tapped = False
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="d", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.permanents["d"].counters.get("p1p1", 0) == 3


def test_broodscale_adapt_creates_spawn():
    brood = _compile("Basking Broodscale").semantics
    ex = Executor({brood.oracle_id: brood})
    state = _state(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=brood.oracle_id,
                name=brood.name,
                is_creature=True,
                power=2,
                toughness=2,
            )
        },
        mana=ManaAmount(colorless=1, green=1),
    )
    ab = next(a for a in brood.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="b", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.permanents["b"].counters.get("p1p1", 0) == 1
    assert state.pending_triggers
    before = len(state.permanents)
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert len(state.permanents) == before + 1


def test_biomancer_draws_on_adapt():
    bio = _compile("Benthic Biomancer").semantics
    ex = Executor({bio.oracle_id: bio})
    state = _state(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=bio.oracle_id,
                name=bio.name,
                is_creature=True,
                power=1,
                toughness=1,
            )
        },
        mana=ManaAmount(colorless=1, blue=1),
    )
    ab = next(a for a in bio.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="b", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.event_counters.get("draw", 0) == 1
