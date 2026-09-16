"""M5 E13b: ETB untap / Warstorm / landfall / artifact-ETB remainders."""

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


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e13b_cards_complete():
    for key in (
        "Blasting Station",
        "Hyrax Tower Scout",
        "Warstorm Surge",
        "Sporemound",
        "Molten Gatekeeper",
        "Yotian Dissident",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_blasting_station_untaps_on_creature_etb():
    station = _compile("Blasting Station").semantics
    fodder = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({station.oracle_id: station, fodder.oracle_id: fodder})
    state = _state(
        permanents={
            "bs": Permanent(
                object_id="bs",
                oracle_id=station.oracle_id,
                name=station.name,
                is_artifact=True,
                tapped=True,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["c"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["bs"].tapped is False


def test_hyrax_untaps_target_creature():
    hyrax = _compile("Hyrax Tower Scout").semantics
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({hyrax.oracle_id: hyrax, dork.oracle_id: dork})
    state = _state(
        permanents={
            "h": Permanent(
                object_id="h",
                oracle_id=hyrax.oracle_id,
                name=hyrax.name,
                is_creature=True,
                power=2,
                toughness=3,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["h"])
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="d")
        )
        is None
    )
    assert state.permanents["d"].tapped is False


def test_hyrax_rejects_noncreature_target():
    hyrax = _compile("Hyrax Tower Scout").semantics
    rock = CardSemantics(
        oracle_id="oracle:rock",
        name="Rock",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({hyrax.oracle_id: hyrax, rock.oracle_id: rock})
    state = _state(
        permanents={
            "h": Permanent(
                object_id="h",
                oracle_id=hyrax.oracle_id,
                name=hyrax.name,
                is_creature=True,
                power=2,
                toughness=3,
            ),
            "r": Permanent(
                object_id="r",
                oracle_id=rock.oracle_id,
                name="Rock",
                is_artifact=True,
                tapped=True,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["h"])
    err = ex.resolve_trigger(state, ActionStep(op="resolve_trigger", target="r"))
    assert err is not None
    assert state.permanents["r"].tapped is True


def test_warstorm_deals_subject_power():
    surge = _compile("Warstorm Surge").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({surge.oracle_id: surge, beater.oracle_id: beater})
    state = _state(
        permanents={
            "w": Permanent(
                object_id="w",
                oracle_id=surge.oracle_id,
                name=surge.name,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=4,
                toughness=4,
            ),
        },
        life_opponent=40,
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["b"])
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="opponent")
        )
        is None
    )
    assert state.life_opponent == 36


def test_sporemound_landfall_creates_saproling():
    mound = _compile("Sporemound").semantics
    land = CardSemantics(
        oracle_id="oracle:forest",
        name="Forest",
        types=["Basic", "Land", "Forest"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({mound.oracle_id: mound, land.oracle_id: land})
    state = _state(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=mound.oracle_id,
                name=mound.name,
                is_creature=True,
                power=3,
                toughness=3,
            ),
            "l": Permanent(
                object_id="l",
                oracle_id=land.oracle_id,
                name="Forest",
            ),
        }
    )
    before = len(state.permanents)
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["l"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert len(state.permanents) == before + 1
    token = next(p for p in state.permanents.values() if p.is_token)
    assert token.is_creature and token.power == 1 and token.toughness == 1


def test_molten_gatekeeper_damages_on_other_etb():
    gate = _compile("Molten Gatekeeper").semantics
    buddy = CardSemantics(
        oracle_id="oracle:buddy",
        name="Buddy",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({gate.oracle_id: gate, buddy.oracle_id: buddy})
    state = _state(
        permanents={
            "g": Permanent(
                object_id="g",
                oracle_id=gate.oracle_id,
                name=gate.name,
                is_creature=True,
                is_artifact=True,
                power=2,
                toughness=3,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=buddy.oracle_id,
                name="Buddy",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        life_opponent=20,
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["b"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 19


def test_yotian_puts_p1p1_on_artifact_etb():
    yotian = _compile("Yotian Dissident").semantics
    art = CardSemantics(
        oracle_id="oracle:art",
        name="Gizmo",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({yotian.oracle_id: yotian, art.oracle_id: art})
    state = _state(
        permanents={
            "y": Permanent(
                object_id="y",
                oracle_id=yotian.oracle_id,
                name=yotian.name,
                is_creature=True,
                power=1,
                toughness=1,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=art.oracle_id,
                name="Gizmo",
                is_artifact=True,
            ),
        }
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["a"])
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="y")
        )
        is None
    )
    assert state.permanents["y"].counters.get("p1p1", 0) == 1
