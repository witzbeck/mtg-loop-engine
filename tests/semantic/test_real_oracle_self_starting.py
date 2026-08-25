"""M5 path-a curriculum: self-starting COMPLETE cards (no life-gain seed)."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    DealDamageEffect,
    TriggeredAbility,
    UntapEffect,
)
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_viridian_joiner_power_mana_compiles_complete():
    report = _compile("Viridian Joiner")
    assert report.coverage == SemanticCoverage.COMPLETE
    ability = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    effect = ability.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.equal_to_source_power == "green"


def test_impact_tremors_etb_damage_compiles_complete():
    report = _compile("Impact Tremors")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.event == TriggerEvent.ENTER_BATTLEFIELD
    assert isinstance(trig.effects[0], DealDamageEffect)
    assert trig.effects[0].amount == 1


def test_midnight_guard_untaps_self_on_etb():
    report = _compile("Midnight Guard")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], UntapEffect)
    assert trig.effects[0].target == "self"


def test_witty_roastmaster_strips_alliance_prefix():
    report = _compile("Witty Roastmaster")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], DealDamageEffect)


def test_warleaders_call_anthem_irrelevant_damage_modeled():
    report = _compile("Warleader's Call")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], DealDamageEffect)


def test_purphoros_devotion_irrelevant_etb_damage_modeled():
    report = _compile("Purphoros, God of the Forge")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], DealDamageEffect)
    assert trig.effects[0].amount == 2
