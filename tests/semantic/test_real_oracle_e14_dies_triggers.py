"""M5 E14: dies-trigger payoffs."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
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


def test_e14_dies_cards_complete():
    for key in (
        "Pitiless Plunderer",
        "Goblin Sharpshooter",
        "Teysa, Orzhov Scion",
        "Blood Artist",
        "Pawn of Ulamog",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_plunderer_creates_treasure_on_death():
    plunderer = _compile("Pitiless Plunderer").semantics
    fodder = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({plunderer.oracle_id: plunderer, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "p": Permanent(
                object_id="p",
                oracle_id=plunderer.oracle_id,
                name=plunderer.name,
                is_creature=True,
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
    )
    ex.die(state, state.permanents["f"])
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    treasures = [
        p
        for p in state.permanents.values()
        if p.is_token and p.name == "Treasure" and p.zone == Zone.BATTLEFIELD
    ]
    assert len(treasures) == 1


def test_sharpshooter_untaps_on_death():
    sharp = _compile("Goblin Sharpshooter").semantics
    fodder = CardSemantics(
        oracle_id="oracle:fodder2",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({sharp.oracle_id: sharp, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=sharp.oracle_id,
                name=sharp.name,
                is_creature=True,
                tapped=True,
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
    )
    ex.die(state, state.permanents["f"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert not state.permanents["s"].tapped


def test_blood_artist_drain():
    artist = _compile("Blood Artist").semantics
    fodder = CardSemantics(
        oracle_id="oracle:fodder3",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({artist.oracle_id: artist, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=artist.oracle_id,
                name=artist.name,
                is_creature=True,
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
        life_you=20,
        life_opponent=40,
    )
    ex.die(state, state.permanents["f"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 39
    assert state.life_you == 21


def test_teysa_black_dies_spirit():
    teysa = _compile("Teysa, Orzhov Scion").semantics
    black = CardSemantics(
        oracle_id="oracle:black-fodder",
        name="Black Fodder",
        types=["Creature"],
        colors=["B"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({teysa.oracle_id: teysa, black.oracle_id: black})
    state = GameState(
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=teysa.oracle_id,
                name=teysa.name,
                is_creature=True,
                colors=["W", "B"],
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=black.oracle_id,
                name="Black Fodder",
                is_creature=True,
                colors=["B"],
            ),
        },
        mana=ManaAmount(),
    )
    ex.die(state, state.permanents["f"])
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    spirits = [
        p
        for p in state.permanents.values()
        if p.is_token and p.name == "Spirit" and p.zone == Zone.BATTLEFIELD
    ]
    assert len(spirits) == 1


def test_pawn_creates_spawn_including_self():
    pawn = _compile("Pawn of Ulamog").semantics
    ex = Executor({pawn.oracle_id: pawn})
    state = GameState(
        permanents={
            "p": Permanent(
                object_id="p",
                oracle_id=pawn.oracle_id,
                name=pawn.name,
                is_creature=True,
            )
        },
        mana=ManaAmount(),
    )
    ex.die(state, state.permanents["p"])
    # May also queue Blood-Artist-class? only pawn
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    spawns = [
        p
        for p in state.permanents.values()
        if p.is_token and "Spawn" in p.name and p.zone == Zone.BATTLEFIELD
    ]
    assert len(spawns) == 1


def test_dies_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-dies",
        name="Fake Dies",
        oracle_text="Whenever a creature dies, proliferate.",
        types=["Creature"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
