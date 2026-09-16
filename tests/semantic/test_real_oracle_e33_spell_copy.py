"""M5 E33: spell copy / Isochron (Dramatic Reversal, Dualcaster, Twincast)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CastImprintedSpellEffect,
    ManaAmount,
)
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


def test_e33_cards_complete():
    for key in (
        "Dramatic Reversal",
        "Isochron Scepter",
        "Dualcaster Mage",
        "Twincast",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_isochron_imprint_and_cast_dramatic_reversal():
    scepter = _compile("Isochron Scepter").semantics
    dramatic = _compile("Dramatic Reversal").semantics
    rock = _compile("Basalt Monolith Live").semantics
    ex = Executor(
        {
            scepter.oracle_id: scepter,
            dramatic.oracle_id: dramatic,
            rock.oracle_id: rock,
        }
    )
    state = GameState(
        mana=ManaAmount(colorless=2),
        permanents={
            "iso": Permanent(
                object_id="iso",
                oracle_id=scepter.oracle_id,
                name=scepter.name,
                is_artifact=True,
            ),
            "dr": Permanent(
                object_id="dr",
                oracle_id=dramatic.oracle_id,
                name=dramatic.name,
                zone=Zone.HAND,
            ),
            "rock": Permanent(
                object_id="rock",
                oracle_id=rock.oracle_id,
                name=rock.name,
                is_artifact=True,
                tapped=True,
            ),
        },
    )
    # Resolve imprint ETB (already on BF; queue as if just entered).
    imprint = next(
        a
        for a in scepter.abilities
        if getattr(a, "event", None) is not None
    )
    state.pending_triggers.append(
        {
            "source_id": "iso",
            "ability_id": imprint.ability_id,
            "subject_id": "iso",
        }
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["dr"].zone == Zone.EXILE
    assert state.permanents["iso"].imprinted_oracle_id == dramatic.oracle_id

    cast_ab = next(
        a
        for a in scepter.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, CastImprintedSpellEffect) for e in a.effects)
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="iso", ability_id=cast_ab.ability_id),
        )
        is None
    )
    assert state.permanents["rock"].tapped is False
    # Isochron taps for cost, then Dramatic Reversal untaps it with other nonlands.
    assert state.permanents["iso"].tapped is False
    assert state.event_counters.get("cast", 0) >= 1


def test_isochron_hard_negative_no_imprint():
    scepter = _compile("Isochron Scepter").semantics
    ex = Executor({scepter.oracle_id: scepter})
    state = GameState(
        mana=ManaAmount(colorless=2),
        permanents={
            "iso": Permanent(
                object_id="iso",
                oracle_id=scepter.oracle_id,
                name=scepter.name,
                is_artifact=True,
            ),
        },
    )
    cast_ab = next(
        a
        for a in scepter.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, CastImprintedSpellEffect) for e in a.effects)
    )
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="iso", ability_id=cast_ab.ability_id),
    )
    assert err is not None


def test_dualcaster_copies_last_cast_spell():
    dual = _compile("Dualcaster Mage").semantics
    dramatic = _compile("Dramatic Reversal").semantics
    ex = Executor({dual.oracle_id: dual, dramatic.oracle_id: dramatic})
    state = GameState(
        mana=ManaAmount(),
        last_cast_spell_oracle_id=dramatic.oracle_id,
        permanents={
            "d": Permanent(
                object_id="d",
                oracle_id=dual.oracle_id,
                name=dual.name,
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "rock": Permanent(
                object_id="rock",
                oracle_id="oracle:dummy-rock",
                name="Rock",
                is_artifact=True,
                tapped=True,
            ),
        },
    )
    # Dummy rock has no semantics needed for untap-all-nonlands.
    etb = next(a for a in dual.abilities if getattr(a, "event", None) is not None)
    state.pending_triggers.append(
        {
            "source_id": "d",
            "ability_id": etb.ability_id,
            "subject_id": "d",
        }
    )
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["rock"].tapped is False
    assert state.event_counters.get("spell_copy", 0) >= 1
