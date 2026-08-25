"""Proof-irrelevant Oracle clauses compile COMPLETE without blocking eligibility."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.oracle_fixtures import UNSUPPORTED_FIXTURE


def test_keyword_only_lines_compile_complete():
    report = compile_oracle_text(
        oracle_id="oracle:test-flyer",
        name="Test Flyer",
        oracle_text="Flying\nFlash",
        types=["Creature"],
    )
    assert report.coverage == SemanticCoverage.COMPLETE
    assert not report.semantics.unsupported_fragments
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)


def test_enchant_and_equip_lines_are_proof_irrelevant():
    report = compile_oracle_text(
        oracle_id="oracle:test-aura",
        name="Test Aura",
        oracle_text="Enchant creature\nEquip {3}",
        types=["Artifact", "Equipment"],
    )
    assert report.coverage == SemanticCoverage.COMPLETE
    assert len(report.semantics.abilities) == 2


def test_loop_ability_with_flying_still_compiles_complete():
    report = compile_oracle_text(
        oracle_id="oracle:test-beater",
        name="Test Beater",
        oracle_text="Flying\n{T}: Add {R}.",
        types=["Creature"],
    )
    assert report.coverage == SemanticCoverage.COMPLETE
    kinds = {a.kind for a in report.semantics.abilities}
    assert "proof_irrelevant_static" in kinds
    assert "activated" in kinds


def test_unsupported_scepter_still_fail_closed():
    fix = UNSUPPORTED_FIXTURE
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()
