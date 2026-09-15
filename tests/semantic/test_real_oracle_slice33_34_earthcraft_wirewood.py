"""M5 slices 33–34: Earthcraft tap-creature untap-land + Wirewood any-color elves."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import ManaScaleKind, SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    ManaAmount,
    TapCreatureCost,
    UntapEffect,
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


def test_earthcraft_compiles_and_rediscovers_with_drake():
    report = _compile("Earthcraft")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, TapCreatureCost) for c in ab.costs)
    assert isinstance(ab.effects[0], UntapEffect)
    assert ab.effects[0].target == "target_basic_land"
    earthcraft = report.semantics
    drake = _compile("Shrieking Drake").semantics
    found = explore_pair(earthcraft, drake, max_depth=14)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert "Earthcraft" in {c.name for c in found.witness.essential_cards}


def test_wirewood_compiles_and_rediscovers_with_staff():
    report = _compile("Wirewood Channeler")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    effect = ab.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.mana_scale is ManaScaleKind.BATTLEFIELD_ELF
    assert effect.scale_color == "any_color"
    wirewood = report.semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(wirewood, staff, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
