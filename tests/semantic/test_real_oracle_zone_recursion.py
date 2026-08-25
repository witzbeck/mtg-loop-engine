"""Real Oracle zone-recursion + sacrifice curriculum (M4 compiler track 2)."""

from mtg_loop_engine.eval.spellbook_eval import compile_card, evaluate_reference_subset
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile_curriculum(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_live_gravecrawler_compiles_complete_with_cast_from_gy():
    report = _compile_curriculum("Gravecrawler")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(
        getattr(a, "requires_zombie", False) for a in report.semantics.abilities
    )


def test_activated_return_gravecrawler_curriculum_compiles_complete():
    report = _compile_curriculum("GravecrawlerActivatedReturn")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)


def test_real_phyrexian_altar_compiles_complete():
    report = _compile_curriculum("Phyrexian Altar")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)


def test_real_reassembling_skeleton_compiles_complete():
    report = _compile_curriculum("Reassembling Skeleton")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)


def test_activated_return_curriculum_pair_is_compiler_eligible():
    variant = {
        "id": "curriculum-activated-gravecrawler-altar",
        "uses": [
            {"card": {"name": "Gravecrawler"}},
            {"card": {"name": "Phyrexian Altar"}},
        ],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    cards = {
        "gravecrawler": compile_card(
            "oracle:gravecrawler-activated-return",
            REAL_ORACLE_CURRICULUM["GravecrawlerActivatedReturn"].name,
            REAL_ORACLE_CURRICULUM["GravecrawlerActivatedReturn"].oracle_text,
            REAL_ORACLE_CURRICULUM["GravecrawlerActivatedReturn"].types,
        ),
        "phyrexian altar": compile_card(
            "oracle:phyrexian-altar",
            REAL_ORACLE_CURRICULUM["Phyrexian Altar"].name,
            REAL_ORACLE_CURRICULUM["Phyrexian Altar"].oracle_text,
            REAL_ORACLE_CURRICULUM["Phyrexian Altar"].types,
        ),
    }
    report = evaluate_reference_subset([variant], cards_by_name=cards)
    assert report.counts.eligible >= 1
    assert report.counts.compiler_unsupported == 0
