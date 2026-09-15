"""M5 slices 29–30: Temur activated bounce + Cloudstone type-share bounce."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    ManaAmount,
    MoveToZoneEffect,
    TriggeredAbility,
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


def test_temur_compiles_and_rediscovers_with_bell_ringer():
    report = _compile("Temur Sabertooth")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert isinstance(ab.effects[0], MoveToZoneEffect)
    assert ab.effects[0].target == "other_controlled_creature"
    assert ab.effects[0].zone == Zone.HAND
    temur = report.semantics
    bell = _compile("Village Bell-Ringer").semantics
    found = explore_pair(temur, bell, max_depth=14)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert "Temur Sabertooth" in {c.name for c in found.witness.essential_cards}


def test_cloudstone_compiles_and_rediscovers_with_aluren():
    report = _compile("Cloudstone Curio")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.filter == "controlled_nonartifact"
    assert trig.effects[0].target == "other_controlled_sharing_type"
    curio = report.semantics
    aluren = _compile("Aluren").semantics
    found = explore_pair(curio, aluren, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert "Cloudstone Curio" in {c.name for c in found.witness.essential_cards}
