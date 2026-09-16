"""M5 E10: multi / targeted land untap."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    ManaAmount,
    TriggeredAbility,
    UntapEffect,
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


def test_e10_land_untap_cards_complete():
    for key in (
        "Palinchron",
        "Peregrine Drake",
        "Cloud of Faeries",
        "Argothian Elder",
        "Ley Weaver",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_etb_untap_up_to_lands():
    drake = _compile("Peregrine Drake").semantics
    land_sem = CardSemantics(
        oracle_id="oracle:basic-island",
        name="Island",
        types=["Basic", "Land", "Island"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({drake.oracle_id: drake, land_sem.oracle_id: land_sem})
    lands = {
        f"l{i}": Permanent(
            object_id=f"l{i}",
            oracle_id=land_sem.oracle_id,
            name="Island",
            tapped=True,
        )
        for i in range(6)
    }
    state = GameState(
        permanents={
            "d": Permanent(
                object_id="d",
                oracle_id=drake.oracle_id,
                name=drake.name,
                is_creature=True,
                power=2,
                toughness=3,
            ),
            **lands,
        },
        mana=ManaAmount(),
    )
    # Queue ETB directly (cast mana accounting is out of scope for this unit).
    from mtg_loop_engine.semantics.enums import TriggerEvent

    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["d"])
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    untapped = sum(1 for i in range(6) if not state.permanents[f"l{i}"].tapped)
    assert untapped == 5
    assert state.permanents["l5"].tapped  # 6th remains tapped


def test_tap_untap_two_lands():
    elder = _compile("Argothian Elder").semantics
    ab = next(a for a in elder.abilities if isinstance(a, ActivatedAbility))
    assert isinstance(ab.effects[0], UntapEffect)
    assert ab.effects[0].quantity == 2
    land_sem = CardSemantics(
        oracle_id="oracle:forest",
        name="Forest",
        types=["Basic", "Land", "Forest"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({elder.oracle_id: elder, land_sem.oracle_id: land_sem})
    state = GameState(
        permanents={
            "e": Permanent(
                object_id="e",
                oracle_id=elder.oracle_id,
                name=elder.name,
                is_creature=True,
                summoning_sick=False,
            ),
            "a": Permanent(
                object_id="a", oracle_id=land_sem.oracle_id, name="Forest", tapped=True
            ),
            "b": Permanent(
                object_id="b", oracle_id=land_sem.oracle_id, name="Forest", tapped=True
            ),
            "c": Permanent(
                object_id="c", oracle_id=land_sem.oracle_id, name="Forest", tapped=True
            ),
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="e", ability_id=ab.ability_id))
        is None
    )
    assert not state.permanents["a"].tapped
    assert not state.permanents["b"].tapped
    assert state.permanents["c"].tapped


def test_wrong_untap_lands_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-untap",
        name="Fake Untap",
        oracle_text="When this creature enters, untap all your mana rocks.",
        types=["Creature"],
        mana_cost=ManaAmount(blue=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
