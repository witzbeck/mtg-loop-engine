"""M5 path-a slice 17: Sliver Queen mana-activated token create."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import default_initial_state, explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CreateTokenEffect,
    ManaAmount,
    ManaCost,
)
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def _ashnod():
    fix = GOLD_ORACLE_FIXTURES["oracle:ashnods-altar"]
    return compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    ).semantics


def test_sliver_queen_compiles_mana_create_token():
    report = _compile("Sliver Queen")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(
        isinstance(c, ManaCost) and c.amount == ManaAmount(generic=2) for c in ab.costs
    )
    effect = ab.effects[0]
    assert isinstance(effect, CreateTokenEffect)
    assert effect.power == 1 and effect.toughness == 1
    assert "Sliver" in effect.name


def test_sliver_queen_create_token_requires_mana():
    queen = _compile("Sliver Queen").semantics
    ab = next(a for a in queen.abilities if isinstance(a, ActivatedAbility))
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("queen", queen.oracle_id, queen.name, is_creature=True),
            ],
            mana=ManaAmount(),
        )
    )
    ex = Executor({queen.oracle_id: queen})
    err = ex.run_step(
        state,
        ActionStep(op="activate", actor="queen", ability_id=ab.ability_id),
    )
    assert err is not None
    assert err.status == VerificationStatus.RESOURCE_DEFICIT


def test_queen_ashnod_seeds_token_fodder():
    queen = _compile("Sliver Queen").semantics
    ash = _ashnod()
    spec = default_initial_state(queen, ash)
    assert any(p.is_token for p in spec.permanents)


def test_sliver_queen_plus_ashnod_discovers():
    queen = _compile("Sliver Queen").semantics
    ash = _ashnod()
    found = explore_pair(queen, ash, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Sliver Queen", "Ashnod's Altar"}


def test_sliver_queen_without_sac_outlet_does_not_verify():
    queen = _compile("Sliver Queen").semantics
    for partner_key in ("Impact Tremors", "Basalt Monolith Live"):
        partner = _compile(partner_key).semantics
        found = explore_pair(queen, partner, max_depth=8)
        assert found is None, f"expected no verified loop for Queen + {partner_key}"
