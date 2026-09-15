"""M5 slice 35: Squirrel Nest enchanted-land tap-token + Earthcraft rediscovery."""

from mtg_loop_engine.search.explorer import (
    BASIC_ISLAND_SEED_ORACLE_ID,
    default_initial_state,
    explore_pair,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ActivatedAbility, CreateTokenEffect, ManaAmount, TapCost
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


def test_squirrel_nest_compiles_land_host_tap_token():
    report = _compile("Squirrel Nest")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, TapCost) and not c.source_self and c.host == "land" for c in ab.costs)
    assert isinstance(ab.effects[0], CreateTokenEffect)
    assert "Squirrel" in ab.effects[0].name


def test_nest_seeds_basic_island_host():
    nest = _compile("Squirrel Nest").semantics
    earthcraft = _compile("Earthcraft").semantics
    spec = default_initial_state(nest, earthcraft)
    assert any(p.oracle_id == BASIC_ISLAND_SEED_ORACLE_ID for p in spec.permanents)


def test_squirrel_nest_plus_earthcraft_rediscovers():
    nest = _compile("Squirrel Nest").semantics
    earthcraft = _compile("Earthcraft").semantics
    found = explore_pair(nest, earthcraft, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Squirrel Nest", "Earthcraft"}
    assert found.witness.classification.generic_prerequisites
    assert any(
        "Island" in p.description or "island" in p.description.lower()
        for p in found.witness.classification.generic_prerequisites
    )


def test_squirrel_nest_alone_does_not_verify():
    nest = _compile("Squirrel Nest").semantics
    # Partner with a COMPLETE non-untap enchantment: no land-untap feedback.
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(nest, alarm, max_depth=10)
    assert found is None
