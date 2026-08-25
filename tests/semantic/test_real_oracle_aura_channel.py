"""M5 aura-channel curriculum: Freed / Pemmin's class."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, TapEffect, UntapEffect
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_freed_from_the_real_compiles_complete_with_tap_and_untap():
    report = _compile("Freed from the Real")
    assert report.coverage == SemanticCoverage.COMPLETE
    activated = [a for a in report.semantics.abilities if isinstance(a, ActivatedAbility)]
    assert len(activated) == 2
    effects = [type(e).__name__ for a in activated for e in a.effects]
    assert "UntapEffect" in effects
    assert "TapEffect" in effects
    assert all(
        isinstance(e, (UntapEffect, TapEffect)) and e.target == "target_permanent"
        for a in activated
        for e in a.effects
    )


def test_pemmins_aura_compiles_complete_untap_plus_irrelevant_riders():
    report = _compile("Pemmin's Aura")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert not report.semantics.unsupported_fragments
    untap = [
        a
        for a in report.semantics.abilities
        if isinstance(a, ActivatedAbility)
        and any(isinstance(e, UntapEffect) for e in a.effects)
    ]
    assert len(untap) == 1
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)
