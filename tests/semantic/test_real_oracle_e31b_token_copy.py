"""M5 E31b: tap-copy siblings (Reflection / Orthion / Myr Propagator)."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, CreateTokenEffect
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e31b_cards_complete():
    for key in (
        "Reflection of Kiki-Jiki",
        "Orthion, Hero of Lavabrink",
        "Myr Propagator",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_reflection_is_paid_tap_copy_haste():
    report = _compile("Reflection of Kiki-Jiki")
    ab = report.semantics.abilities[0]
    assert isinstance(ab, ActivatedAbility)
    assert len(ab.costs) == 2
    assert isinstance(ab.effects[0], CreateTokenEffect)
    assert ab.effects[0].copy_target and ab.effects[0].haste
