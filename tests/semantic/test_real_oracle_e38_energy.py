"""M5 E38: energy counters (Basker, Lightning Runner, Stone Idol)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
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


def test_e38_cards_complete():
    for key in (
        "Aetherwind Basker",
        "Lightning Runner",
        "Stone Idol Generator",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_basker_etb_gets_energy():
    basker = _compile("Aetherwind Basker").semantics
    ex = Executor({basker.oracle_id: basker})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=basker.oracle_id,
                name=basker.name,
                is_creature=True,
                power=7,
                toughness=7,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id="oracle:c",
                name="Creature",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    ab = next(
        a
        for a in basker.abilities
        if getattr(a, "event", None) == TriggerEvent.ENTER_BATTLEFIELD
    )
    state.pending_triggers.append(
        {"source_id": "b", "ability_id": ab.ability_id, "subject_id": "b"}
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.energy_you == 2


def test_pay_energy_untap_and_hard_negative():
    runner = _compile("Lightning Runner").semantics
    ex = Executor({runner.oracle_id: runner})
    state = GameState(
        mana=ManaAmount(),
        energy_you=8,
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=runner.oracle_id,
                name=runner.name,
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id="oracle:c",
                name="Creature",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
        },
    )
    ab = next(a for a in runner.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="r", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.energy_you == 0
    assert state.permanents["c"].tapped is False
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="r", ability_id=ab.ability_id),
    )
    assert err is not None
