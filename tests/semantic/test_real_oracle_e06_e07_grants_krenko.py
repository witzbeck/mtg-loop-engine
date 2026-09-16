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


def test_krenko_plus_alarm_rediscovers():
    krenko = _compile("Krenko, Mob Boss").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(krenko, alarm, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert "Krenko, Mob Boss" in names
    assert "Intruder Alarm" in names
