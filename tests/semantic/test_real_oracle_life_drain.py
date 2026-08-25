"""M5 life-drain curriculum: Vito / Bond / Exquisite Blood class."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import GainLifeEffect, LoseLifeEffect, TriggeredAbility
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_sanguine_bond_and_exquisite_blood_compile_complete():
    bond = _compile("Sanguine Bond")
    blood = _compile("Exquisite Blood")
    assert bond.coverage == SemanticCoverage.COMPLETE
    assert blood.coverage == SemanticCoverage.COMPLETE
    bond_tr = next(a for a in bond.semantics.abilities if isinstance(a, TriggeredAbility))
    blood_tr = next(a for a in blood.semantics.abilities if isinstance(a, TriggeredAbility))
    assert bond_tr.event == TriggerEvent.GAIN_LIFE
    assert isinstance(bond_tr.effects[0], LoseLifeEffect)
    assert bond_tr.effects[0].amount_from_trigger is True
    assert blood_tr.event == TriggerEvent.OPPONENT_LOSE_LIFE
    assert isinstance(blood_tr.effects[0], GainLifeEffect)
    assert blood_tr.effects[0].amount_from_trigger is True


def test_vito_compiles_complete_with_irrelevant_lifelink_activation():
    report = _compile("Vito, Thorn of the Dusk Rose")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)
