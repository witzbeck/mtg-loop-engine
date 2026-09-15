"""M5 slice 36: Patrol Signaler paid {Q} create + Earthcraft rediscovery."""

from mtg_loop_engine.search.explorer import (
    BASIC_PLAINS_SEED_ORACLE_ID,
    default_initial_state,
    explore_pair,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CreateTokenEffect,
    ManaAmount,
    ManaCost,
    UntapSymbolCost,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-")
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


def test_patrol_signaler_compiles_mana_untap_create():
    report = _compile("Patrol Signaler")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, ManaCost) and c.amount.white == 1 for c in ab.costs)
    assert any(isinstance(c, UntapSymbolCost) and c.source_self for c in ab.costs)
    assert isinstance(ab.effects[0], CreateTokenEffect)


def test_signaler_seeds_basic_plains_with_earthcraft():
    signaler = _compile("Patrol Signaler").semantics
    earthcraft = _compile("Earthcraft").semantics
    spec = default_initial_state(signaler, earthcraft)
    assert any(p.oracle_id == BASIC_PLAINS_SEED_ORACLE_ID for p in spec.permanents)


def test_patrol_signaler_plus_earthcraft_rediscovers():
    signaler = _compile("Patrol Signaler").semantics
    earthcraft = _compile("Earthcraft").semantics
    found = explore_pair(signaler, earthcraft, max_depth=16)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Patrol Signaler", "Earthcraft"}


def test_patrol_signaler_alone_does_not_verify():
    signaler = _compile("Patrol Signaler").semantics
    nest = _compile("Squirrel Nest").semantics
    found = explore_pair(signaler, nest, max_depth=12)
    assert found is None
