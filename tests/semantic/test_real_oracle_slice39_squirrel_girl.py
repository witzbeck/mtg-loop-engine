"""M5 slice 39: Unbeatable Squirrel Girl ETB create + X=Squirrels mana create."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, ManaAmount
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CreateTokenEffect,
    ManaCost,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-").replace("'", "")
    cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else ManaAmount()
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=cost,
        mana_value=row.mana_value,
    )


def test_squirrel_girl_compiles_complete():
    report = _compile("The Unbeatable Squirrel Girl")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    etb = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.ENTER_BATTLEFIELD
    )
    assert etb.filter == "self"
    assert isinstance(etb.effects[0], CreateTokenEffect)
    assert etb.effects[0].name == "Squirrel"
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, ManaCost) for c in ab.costs)
    create = ab.effects[0]
    assert isinstance(create, CreateTokenEffect)
    assert create.quantity_equal_to_controlled_subtype == "Squirrel"


def test_squirrel_girl_x_create_counts_squirrels():
    sg = _compile("The Unbeatable Squirrel Girl").semantics
    ab = next(a for a in sg.abilities if isinstance(a, ActivatedAbility))
    spec = InitialStateSpec(
        permanents=[
            bf("sg", sg.oracle_id, sg.name, is_creature=True, power=3, toughness=3),
            bf(
                "t0",
                "token:Squirrel",
                "Squirrel",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            ),
        ],
        mana=ManaAmount(green=3, colorless=1),
    )
    ex = Executor({sg.oracle_id: sg})
    state = GameState.from_spec(spec)
    before = sum(1 for p in state.permanents.values() if p.is_token)
    err = ex.run_step(
        state, ActionStep(op="activate", actor="sg", ability_id=ab.ability_id)
    )
    assert err is None
    after = sum(1 for p in state.permanents.values() if p.is_token)
    # SG + 1 squirrel → X=2
    assert after == before + 2


def test_squirrel_girl_plus_altar_rediscovers():
    sg = _compile("The Unbeatable Squirrel Girl").semantics
    altar = _compile("Phyrexian Altar").semantics
    found = explore_pair(sg, altar, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"The Unbeatable Squirrel Girl", "Phyrexian Altar"}
