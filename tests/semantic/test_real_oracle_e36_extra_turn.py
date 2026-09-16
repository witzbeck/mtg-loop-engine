"""M5 E36: extra turn (Time Warp, Temporal Manipulation, Magistrate's Scepter)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, ExtraTurnEffect, ManaAmount
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e36_cards_complete():
    for key in ("Time Warp", "Temporal Manipulation", "Magistrate's Scepter"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_scepter_extra_turn_with_charges():
    scepter = _compile("Magistrate's Scepter").semantics
    ex = Executor({scepter.oracle_id: scepter})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=scepter.oracle_id,
                name=scepter.name,
                is_artifact=True,
                counters={"charge": 3},
            ),
        },
    )
    ab = next(
        a
        for a in scepter.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, ExtraTurnEffect) for e in a.effects)
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="s", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.event_counters.get("extra_turn", 0) >= 1
    assert state.permanents["s"].counters.get("charge", 0) == 0


def test_scepter_hard_negative_insufficient_charge():
    scepter = _compile("Magistrate's Scepter").semantics
    ex = Executor({scepter.oracle_id: scepter})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=scepter.oracle_id,
                name=scepter.name,
                is_artifact=True,
                counters={"charge": 1},
            ),
        },
    )
    ab = next(
        a
        for a in scepter.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, ExtraTurnEffect) for e in a.effects)
    )
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="s", ability_id=ab.ability_id),
    )
    assert err is not None
