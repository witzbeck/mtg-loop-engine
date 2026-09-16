"""M5 E54: impulse / top-deck (Top, Harnfel impulse, Elven Chorus PI)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaAmount
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e54_cards_complete():
    for key in (
        "Sensei's Divining Top",
        "Harnfel, Horn of Bounty",
        "Elven Chorus",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_top_draw_puts_self_on_library():
    top = _compile("Sensei's Divining Top").semantics
    ex = Executor({top.oracle_id: top})
    state = GameState(
        mana=ManaAmount(),
        hand_you=3,
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=top.oracle_id,
                name=top.name,
                is_artifact=True,
            )
        },
    )
    ab = next(
        a
        for a in top.abilities
        if isinstance(a, ActivatedAbility) and any(c.kind == "tap" for c in a.costs)
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="t", ability_id=ab.ability_id))
        is None
    )
    assert state.hand_you == 4
    assert state.permanents["t"].zone == Zone.LIBRARY
