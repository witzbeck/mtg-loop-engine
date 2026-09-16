"""M5 E13a: self-ETB power / devotion / artifact-scaled effects."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount
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


def test_e13a_cards_complete():
    for key in (
        "Murderous Redcap",
        "Fanatic of Mogis",
        "Gray Merchant of Asphodel",
        "Edgar, King of Figaro",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_redcap_power_damage():
    redcap = _compile("Murderous Redcap").semantics
    ex = Executor({redcap.oracle_id: redcap})
    state = GameState(
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=redcap.oracle_id,
                name=redcap.name,
                is_creature=True,
                power=2,
                toughness=2,
            )
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["r"])
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="opponent")
        )
        is None
    )
    assert state.life_opponent == 38


def test_gary_devotion_drain():
    gary = _compile("Gray Merchant of Asphodel").semantics
    # Gary itself contributes 2 black; seed another black permanent cost
    dork = CardSemantics(
        oracle_id="oracle:black-dork",
        name="Black Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_cost=ManaAmount(black=2),
        mana_value=2,
    )
    ex = Executor({gary.oracle_id: gary, dork.oracle_id: dork})
    state = GameState(
        permanents={
            "g": Permanent(
                object_id="g",
                oracle_id=gary.oracle_id,
                name=gary.name,
                is_creature=True,
                power=2,
                toughness=4,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Black Dork",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
        life_you=20,
        life_opponent=40,
    )
    # devotion = gary 2B + dork 2B = 4
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["g"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 36
    assert state.life_you == 24


def test_edgar_draw_artifacts():
    edgar = _compile("Edgar, King of Figaro").semantics
    rock = CardSemantics(
        oracle_id="oracle:rock",
        name="Rock",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({edgar.oracle_id: edgar, rock.oracle_id: rock})
    state = GameState(
        permanents={
            "e": Permanent(
                object_id="e",
                oracle_id=edgar.oracle_id,
                name=edgar.name,
                is_creature=True,
            ),
            "a": Permanent(
                object_id="a", oracle_id=rock.oracle_id, name="Rock", is_artifact=True
            ),
            "b": Permanent(
                object_id="b", oracle_id=rock.oracle_id, name="Rock", is_artifact=True
            ),
        },
        mana=ManaAmount(),
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["e"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.event_counters.get("draw", 0) == 2


def test_etb_scaled_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-etb",
        name="Fake ETB",
        oracle_text="When this creature enters, it deals damage equal to its toughness to any target.",
        types=["Creature"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
