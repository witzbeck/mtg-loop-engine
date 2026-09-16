"""M5 E68: damage-to-you / dealt-damage reflect remainders."""

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


def test_e68_cards_complete():
    for key in ("Mogg Maniac", "Stuffy Doll"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_stuffy_self_ping_reflects_to_opponent():
    doll = _compile("Stuffy Doll").semantics
    ex = Executor({doll.oracle_id: doll})
    state = _state(
        permanents={
            "d": Permanent(
                object_id="d",
                oracle_id=doll.oracle_id,
                name=doll.name,
                is_creature=True,
                is_artifact=True,
                power=0,
                toughness=1,
            )
        },
        life_opponent=20,
    )
    ab = next(a for a in doll.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="d", ability_id=ab.ability_id, target="d"),
        )
        is None
    )
    assert state.permanents["d"].damage_marked == 1
    assert state.pending_triggers
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="opponent")
        )
        is None
    )
    assert state.life_opponent == 19
