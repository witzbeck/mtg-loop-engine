"""M5 E19–E21: bounce-as-cost, counter doubling, proliferate."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    BounceControlledCost,
    CardSemantics,
    ManaAmount,
    ManaCost,
    ProliferateEffect,
    ReplacementDoubleCounters,
    ReplacementDoubleTokens,
    TapCost,
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


def test_e20_doubling_season_and_primal_vigor_complete():
    season = _compile("Doubling Season")
    assert season.coverage == SemanticCoverage.COMPLETE, (
        season.semantics.unsupported_fragments
    )
    kinds = {type(a).__name__ for a in season.semantics.abilities}
    assert "ReplacementDoubleTokens" in kinds
    assert "ReplacementDoubleCounters" in kinds

    vigor = _compile("Primal Vigor")
    assert vigor.coverage == SemanticCoverage.COMPLETE, (
        vigor.semantics.unsupported_fragments
    )
    dbl = next(
        a
        for a in vigor.semantics.abilities
        if isinstance(a, ReplacementDoubleCounters)
    )
    assert dbl.only_p1p1 is True
    assert dbl.applies_to == "creatures_you_control"
    assert any(isinstance(a, ReplacementDoubleTokens) for a in vigor.semantics.abilities)


def test_e21_viral_drake_proliferate_complete():
    report = _compile("Viral Drake")
    assert report.coverage == SemanticCoverage.COMPLETE, (
        report.semantics.unsupported_fragments
    )
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert isinstance(ab.effects[0], ProliferateEffect)


def test_e19_bounce_cost_cards_complete():
    for key in (
        "Quirion Ranger",
        "Wirewood Symbiote",
        "Meloku the Clouded Mirror",
        "Chulane, Teller of Tales",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_doubling_season_doubles_counters():
    season = _compile("Doubling Season").semantics
    putter = CardSemantics(
        oracle_id="oracle:putter",
        name="Putter",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="put",
                costs=[TapCost()],
                effects=[
                    AddCounterEffect(
                        counter_type="p1p1", quantity=1, target="target_other_creature"
                    )
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    host = CardSemantics(
        oracle_id="oracle:host",
        name="Host",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {
            season.oracle_id: season,
            putter.oracle_id: putter,
            host.oracle_id: host,
        }
    )
    state = GameState(
        permanents={
            "season": Permanent(
                object_id="season",
                oracle_id=season.oracle_id,
                name=season.name,
            ),
            "putter": Permanent(
                object_id="putter",
                oracle_id=putter.oracle_id,
                name="Putter",
                is_creature=True,
                power=1,
                toughness=1,
            ),
            "host": Permanent(
                object_id="host",
                oracle_id=host.oracle_id,
                name="Host",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="putter", ability_id="put", target="host"),
        )
        is None
    )
    assert state.permanents["host"].counters.get("p1p1") == 2


def test_proliferate_adds_existing_kinds():
    drake = _compile("Viral Drake").semantics
    host = CardSemantics(
        oracle_id="oracle:host",
        name="Host",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({drake.oracle_id: drake, host.oracle_id: host})
    state = GameState(
        permanents={
            "drake": Permanent(
                object_id="drake",
                oracle_id=drake.oracle_id,
                name=drake.name,
                is_creature=True,
                power=1,
                toughness=4,
            ),
            "host": Permanent(
                object_id="host",
                oracle_id=host.oracle_id,
                name="Host",
                is_creature=True,
                power=1,
                toughness=1,
                counters={"p1p1": 1, "charge": 2},
            ),
        },
        mana=ManaAmount(colorless=3, blue=1),
    )
    ab = next(a for a in drake.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="drake", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.permanents["host"].counters["p1p1"] == 2
    assert state.permanents["host"].counters["charge"] == 3


def test_quirion_bounces_forest_to_untap():
    quirion = _compile("Quirion Ranger").semantics
    forest = CardSemantics(
        oracle_id="oracle:forest",
        name="Forest",
        types=["Basic", "Land", "Forest"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    target = CardSemantics(
        oracle_id="oracle:tapme",
        name="Tapme",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {
            quirion.oracle_id: quirion,
            forest.oracle_id: forest,
            target.oracle_id: target,
        }
    )
    state = GameState(
        permanents={
            "q": Permanent(
                object_id="q",
                oracle_id=quirion.oracle_id,
                name=quirion.name,
                is_creature=True,
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=forest.oracle_id,
                name="Forest",
            ),
            "t": Permanent(
                object_id="t",
                oracle_id=target.oracle_id,
                name="Tapme",
                is_creature=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in quirion.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, BounceControlledCost) for c in ab.costs)
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate",
                actor="q",
                ability_id=ab.ability_id,
                target="t",
                cost_target="f",
            ),
        )
        is None
    )
    assert state.permanents["f"].zone == Zone.HAND
    assert state.permanents["t"].tapped is False


def test_bounce_wrong_fodder_hard_negative():
    quirion = _compile("Quirion Ranger").semantics
    mountain = CardSemantics(
        oracle_id="oracle:mountain",
        name="Mountain",
        types=["Basic", "Land", "Mountain"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    target = CardSemantics(
        oracle_id="oracle:tapme",
        name="Tapme",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {
            quirion.oracle_id: quirion,
            mountain.oracle_id: mountain,
            target.oracle_id: target,
        }
    )
    state = GameState(
        permanents={
            "q": Permanent(
                object_id="q",
                oracle_id=quirion.oracle_id,
                name=quirion.name,
                is_creature=True,
            ),
            "m": Permanent(
                object_id="m",
                oracle_id=mountain.oracle_id,
                name="Mountain",
            ),
            "t": Permanent(
                object_id="t",
                oracle_id=target.oracle_id,
                name="Tapme",
                is_creature=True,
                tapped=True,
            ),
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in quirion.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="q",
            ability_id=ab.ability_id,
            target="t",
            cost_target="m",
        ),
    )
    assert err is not None
    assert state.permanents["m"].zone == Zone.BATTLEFIELD
    assert state.permanents["t"].tapped is True


def test_meloku_creates_token_after_land_bounce():
    meloku = _compile("Meloku the Clouded Mirror").semantics
    island = CardSemantics(
        oracle_id="oracle:island",
        name="Island",
        types=["Basic", "Land", "Island"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({meloku.oracle_id: meloku, island.oracle_id: island})
    state = GameState(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=meloku.oracle_id,
                name=meloku.name,
                is_creature=True,
            ),
            "i": Permanent(
                object_id="i",
                oracle_id=island.oracle_id,
                name="Island",
            ),
        },
        mana=ManaAmount(colorless=1),
    )
    ab = next(a for a in meloku.abilities if isinstance(a, ActivatedAbility))
    before = len(state.permanents)
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate",
                actor="m",
                ability_id=ab.ability_id,
                cost_target="i",
            ),
        )
        is None
    )
    assert state.permanents["i"].zone == Zone.HAND
    assert len(state.permanents) == before + 1
    tokens = [p for p in state.permanents.values() if p.is_token]
    assert len(tokens) == 1
    assert tokens[0].name == "Illusion"
