"""M5 E12: cast-trigger effect family."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount, TriggeredAbility
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


def test_e12_cast_trigger_cards_complete():
    for key in (
        "Birgi, God of Storytelling",
        "Forsaken Monument",
        "Animar, Soul of Elements",
        "Runaway Steam-Kin",
        "Vivi Ornitier",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_birgi_cast_adds_red():
    birgi = _compile("Birgi, God of Storytelling").semantics
    rock = CardSemantics(
        oracle_id="oracle:rock",
        name="Rock",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_cost=ManaAmount(),
        mana_value=0,
    )
    ex = Executor({birgi.oracle_id: birgi, rock.oracle_id: rock})
    state = GameState(
        permanents={
            "b": Permanent(
                object_id="b",
                oracle_id=birgi.oracle_id,
                name=birgi.name,
                is_creature=True,
            ),
            "r": Permanent(
                object_id="r",
                oracle_id=rock.oracle_id,
                name="Rock",
                zone=Zone.HAND,
                is_artifact=True,
            ),
        },
        mana=ManaAmount(),
    )
    assert ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="r")) is None
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.mana.red == 1


def test_animar_creature_cast_counter():
    animar = _compile("Animar, Soul of Elements").semantics
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_cost=ManaAmount(),
        mana_value=0,
    )
    ex = Executor({animar.oracle_id: animar, dork.oracle_id: dork})
    state = GameState(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=animar.oracle_id,
                name=animar.name,
                is_creature=True,
                power=1,
                toughness=1,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                zone=Zone.HAND,
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
    )
    assert ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="d")) is None
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["a"].counters.get("p1p1", 0) == 1


def test_steam_kin_cap_intervening_if():
    steam = _compile("Runaway Steam-Kin").semantics
    ab = next(a for a in steam.abilities if isinstance(a, TriggeredAbility))
    assert ab.intervening_if == "fewer_than_three_p1p1"
    red = CardSemantics(
        oracle_id="oracle:red-rock",
        name="Red Rock",
        types=["Artifact"],
        colors=["R"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_cost=ManaAmount(),
        mana_value=0,
    )
    ex = Executor({steam.oracle_id: steam, red.oracle_id: red})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=steam.oracle_id,
                name=steam.name,
                is_creature=True,
                counters={"p1p1": 3},
            ),
            "r": Permanent(
                object_id="r",
                oracle_id=red.oracle_id,
                name="Red Rock",
                zone=Zone.HAND,
                is_artifact=True,
                colors=["R"],
            ),
        },
        mana=ManaAmount(),
    )
    assert ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="r")) is None
    # Cap: intervening-if blocks queue
    assert state.pending_triggers == []


def test_cast_trigger_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-cast",
        name="Fake Cast",
        oracle_text="Whenever you cast a spell, proliferate.",
        types=["Creature"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
