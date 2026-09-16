"""M5 E74: fight / enrage (Polyraptor, Brash Taunter, Apex Altisaur)."""

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


def test_e74_cards_complete():
    for key in ("Polyraptor", "Brash Taunter", "Apex Altisaur"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_polyraptor_enrage_creates_copy():
    poly = _compile("Polyraptor").semantics
    ex = Executor({poly.oracle_id: poly})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "p": Permanent(
                object_id="p",
                oracle_id=poly.oracle_id,
                name=poly.name,
                is_creature=True,
                power=5,
                toughness=5,
            ),
        },
    )
    ab = next(a for a in poly.abilities if getattr(a, "event", None) == TriggerEvent.DEALT_DAMAGE)
    state.pending_triggers.append(
        {"source_id": "p", "ability_id": ab.ability_id, "subject_id": "p", "amount": 1}
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    tokens = [p for p in state.permanents.values() if p.is_token]
    assert len(tokens) == 1
    assert tokens[0].oracle_id == poly.oracle_id


def test_brash_taunter_fight_and_hard_negative_self():
    taunter = _compile("Brash Taunter").semantics
    ex = Executor({taunter.oracle_id: taunter})
    state = GameState(
        mana=ManaAmount(red=1, colorless=2),
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=taunter.oracle_id,
                name=taunter.name,
                is_creature=True,
                power=3,
                toughness=3,
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=taunter.oracle_id,
                name="Fodder",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    fight = next(a for a in taunter.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate", actor="t", ability_id=fight.ability_id, target="f"
            ),
        )
        is None
    )
    assert state.event_counters.get("fight", 0) >= 1
    err = ex.activate(
        state,
        ActionStep(
            op="activate", actor="t", ability_id=fight.ability_id, target="t"
        ),
    )
    assert err is not None
