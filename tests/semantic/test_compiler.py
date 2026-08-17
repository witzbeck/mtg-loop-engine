"""Tests for Oracle ability splitting and pattern compilation."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text, split_oracle_abilities
from mtg_loop_engine.semantics.coverage import aggregate_coverage
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.oracle_fixtures import (
    GOLD_ORACLE_FIXTURES,
    UNSUPPORTED_FIXTURE,
)


def test_split_basalt_two_abilities():
    text = GOLD_ORACLE_FIXTURES["oracle:basalt-monolith"].oracle_text
    parts = split_oracle_abilities(text)
    assert len(parts) == 2
    assert parts[0].startswith("{T}:")
    assert "Untap" in parts[1]


def test_compile_basalt_complete():
    fix = GOLD_ORACLE_FIXTURES["oracle:basalt-monolith"]
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    assert report.coverage == SemanticCoverage.COMPLETE
    assert len(report.semantics.abilities) == 2
    kinds = {a.kind for a in report.semantics.abilities}
    assert kinds == {"activated"}


def test_compile_all_gold_fixtures_high_coverage():
    reports = []
    for fix in GOLD_ORACLE_FIXTURES.values():
        report = compile_oracle_text(
            oracle_id=fix.oracle_id,
            name=fix.name,
            oracle_text=fix.oracle_text,
            types=fix.types,
        )
        reports.append(report)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            f"{fix.name}: unsupported={report.semantics.unsupported_fragments}"
        )
    metrics = aggregate_coverage(reports)
    assert metrics.fragment_coverage == 1.0
    assert metrics.cards_complete == len(GOLD_ORACLE_FIXTURES)


def test_unsupported_scepter_fails_closed():
    fix = UNSUPPORTED_FIXTURE
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.unsupported_fragments
    assert report.semantics.relevant_unsupported()
