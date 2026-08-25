"""M5 activated-artifact + Intruder Alarm live Oracle curriculum."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    DrawEffect,
    GainLifeEffect,
    TriggeredAbility,
    UntapEffect,
)
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_staff_of_domination_compiles_complete():
    report = _compile("Staff of Domination")
    assert report.coverage == SemanticCoverage.COMPLETE
    activated = [a for a in report.semantics.abilities if isinstance(a, ActivatedAbility)]
    assert len(activated) == 5
    assert any(
        isinstance(e, GainLifeEffect) for a in activated for e in a.effects
    )
    assert any(isinstance(e, DrawEffect) for a in activated for e in a.effects)
    assert any(
        isinstance(e, UntapEffect) and e.target == "self"
        for a in activated
        for e in a.effects
    )


def test_live_basalt_monolith_compiles_complete():
    report = _compile("Basalt Monolith Live")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)


def test_live_intruder_alarm_untaps_all_creatures():
    report = _compile("Intruder Alarm Live")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = [
        a for a in report.semantics.abilities if isinstance(a, TriggeredAbility)
    ]
    assert len(trig) == 1
    assert trig[0].effects[0].target == "all_creatures"
