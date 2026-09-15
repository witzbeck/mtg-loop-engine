"""M5 slices 26–28: ETB bounce target variants (Fleetfoot / Dream / Statue)."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import ManaAmount, MoveToZoneEffect, TriggeredAbility
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


def test_fleetfoot_compiles_and_rediscovers_with_aluren():
    report = _compile("Fleetfoot Panther")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], MoveToZoneEffect)
    assert trig.effects[0].target == "controlled_creature_green_or_white"
    panther = report.semantics
    aluren = _compile("Aluren").semantics
    found = explore_pair(panther, aluren, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert "Fleetfoot Panther" in {c.name for c in found.witness.essential_cards}


def test_dream_stalker_compiles_and_rediscovers_with_alarm():
    report = _compile("Dream Stalker")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.effects[0].target == "controlled_permanent"
    assert trig.effects[0].zone == Zone.HAND
    dream = report.semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(dream, alarm, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED


def test_ancestral_statue_compiles_and_rediscovers_with_alarm():
    report = _compile("Ancestral Statue")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.effects[0].target == "controlled_nonland"
    statue = report.semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(statue, alarm, max_depth=14)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
