"""M5 E06/E07: grant activated abilities + Krenko-scale create."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    CreateTokenEffect,
    GrantActivatedAbility,
    ManaAmount,
)
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


def test_e06_grant_cards_complete():
    for key in ("Cryptolith Rite", "Basal Sliver", "Resplendent Mentor"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )
        assert any(isinstance(a, GrantActivatedAbility) for a in report.semantics.abilities)


def test_e07_krenko_complete():
    report = _compile("Krenko, Mob Boss")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    effect = ab.effects[0]
    assert isinstance(effect, CreateTokenEffect)
    assert effect.quantity_equal_to_controlled_subtype.lower() == "goblin"


def test_cryptolith_grant_pays_mana_on_creature():
    rite = _compile("Cryptolith Rite").semantics
    dork = CardSemantics(
        oracle_id="oracle:plain-dork",
        name="Plain Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({rite.oracle_id: rite, dork.oracle_id: dork})
    state = GameState(
        permanents={
            "rite": Permanent(object_id="rite", oracle_id=rite.oracle_id, name=rite.name),
            "dork": Permanent(
                object_id="dork",
                oracle_id=dork.oracle_id,
                name="Plain Dork",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
    )
    grants = ex.iter_granted_activated(state, state.permanents["dork"])
    assert len(grants) == 1
    aid = grants[0].ability_id
    assert (
        ex.activate(state, ActionStep(op="activate", actor="dork", ability_id=aid))
        is None
    )
    assert state.mana.any_color == 1


def test_basal_sliver_grant_sac_mana():
    basal = _compile("Basal Sliver").semantics
    fodder = CardSemantics(
        oracle_id="oracle:sliver-fodder",
        name="Sliver Fodder",
        types=["Creature", "Sliver"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({basal.oracle_id: basal, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "basal": Permanent(
                object_id="basal",
                oracle_id=basal.oracle_id,
                name=basal.name,
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "fodder": Permanent(
                object_id="fodder",
                oracle_id=fodder.oracle_id,
                name="Sliver Fodder",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
    )
    grants = ex.iter_granted_activated(state, state.permanents["fodder"])
    assert grants
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="fodder", ability_id=grants[0].ability_id),
        )
        is None
    )
    assert state.mana.black == 2
    assert state.permanents["fodder"].zone.value == "graveyard"


def test_resplendent_grant_white_only():
    mentor = _compile("Resplendent Mentor").semantics
    white = CardSemantics(
        oracle_id="oracle:white-creature",
        name="White Creature",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        colors=["W"],
    )
    red = CardSemantics(
        oracle_id="oracle:red-creature",
        name="Red Creature",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        colors=["R"],
    )
    ex = Executor(
        {mentor.oracle_id: mentor, white.oracle_id: white, red.oracle_id: red}
    )
    state = GameState(
        permanents={
            "mentor": Permanent(
                object_id="mentor",
                oracle_id=mentor.oracle_id,
                name=mentor.name,
                is_creature=True,
                colors=["W"],
                power=2,
                toughness=2,
            ),
            "white": Permanent(
                object_id="white",
                oracle_id=white.oracle_id,
                name="White Creature",
                is_creature=True,
                colors=["W"],
                power=1,
                toughness=1,
            ),
            "red": Permanent(
                object_id="red",
                oracle_id=red.oracle_id,
                name="Red Creature",
                is_creature=True,
                colors=["R"],
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
        life_you=40,
    )
    assert ex.iter_granted_activated(state, state.permanents["white"])
    assert not ex.iter_granted_activated(state, state.permanents["red"])
    aid = ex.iter_granted_activated(state, state.permanents["white"])[0].ability_id
    assert (
        ex.activate(state, ActionStep(op="activate", actor="white", ability_id=aid))
        is None
    )
    assert state.life_you == 41
