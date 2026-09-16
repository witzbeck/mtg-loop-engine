"""M5 E60: tap-for-draw family."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, CardSemantics, ManaAmount, TapCreatureCost
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


def test_e60_draw_cards_complete():
    for key in (
        "Arcanis the Omnipotent",
        "Azami, Lady of Scrolls",
        "Temple Bell",
        "Kwain, Itinerant Meddler",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_arcanis_draws_three():
    arc = _compile("Arcanis the Omnipotent").semantics
    ex = Executor({arc.oracle_id: arc})
    state = GameState(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=arc.oracle_id,
                name=arc.name,
                is_creature=True,
            )
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in arc.abilities if isinstance(a, ActivatedAbility))
    assert ab.effects[0].amount == 3
    assert (
        ex.activate(state, ActionStep(op="activate", actor="a", ability_id=ab.ability_id))
        is None
    )
    assert state.event_counters.get("draw", 0) == 3


def test_azami_requires_wizard_fodder():
    azami = _compile("Azami, Lady of Scrolls").semantics
    wizard = CardSemantics(
        oracle_id="oracle:wiz",
        name="Apprentice",
        types=["Creature", "Wizard"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    beast = CardSemantics(
        oracle_id="oracle:beast",
        name="Beast",
        types=["Creature", "Beast"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {azami.oracle_id: azami, wizard.oracle_id: wizard, beast.oracle_id: beast}
    )
    ab = next(a for a in azami.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, TapCreatureCost) and c.subtype == "Wizard" for c in ab.costs)
    state = GameState(
        permanents={
            "az": Permanent(
                object_id="az",
                oracle_id=azami.oracle_id,
                name=azami.name,
                is_creature=True,
            ),
            "w": Permanent(
                object_id="w",
                oracle_id=wizard.oracle_id,
                name="Apprentice",
                is_creature=True,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beast.oracle_id,
                name="Beast",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
    )
    bad = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="az",
            ability_id=ab.ability_id,
            cost_target="b",
        ),
    )
    assert bad is not None
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate",
                actor="az",
                ability_id=ab.ability_id,
                cost_target="w",
            ),
        )
        is None
    )
    assert state.permanents["w"].tapped is True
    assert state.event_counters.get("draw", 0) == 1


def test_temple_bell_draws():
    bell = _compile("Temple Bell").semantics
    ex = Executor({bell.oracle_id: bell})
    state = GameState(
        permanents={
            "t": Permanent(object_id="t", oracle_id=bell.oracle_id, name=bell.name)
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in bell.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(state, ActionStep(op="activate", actor="t", ability_id=ab.ability_id))
        is None
    )
    assert state.event_counters.get("draw", 0) == 1
