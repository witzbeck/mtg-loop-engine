"""Real Oracle zone-recursion + sacrifice curriculum (M4 compiler track 2)."""

from mtg_loop_engine.eval.spellbook_eval import compile_card, evaluate_reference_subset
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.semantics.compiler import compile_oracle_text


def _compile_curriculum(name: str):
    row = REAL_ORACLE_CURRICULUM[name]
    return compile_oracle_text(
        oracle_id=f"oracle:{name.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_real_gravecrawler_compiles_complete():
    report = _compile_curriculum("Gravecrawler")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)


def test_real_phyrexian_altar_compiles_complete():
    report = _compile_curriculum("Phyrexian Altar")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)


def test_real_reassembling_skeleton_compiles_complete():
    report = _compile_curriculum("Reassembling Skeleton")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "activated" for a in report.semantics.abilities)


def test_spellbook_gravecrawler_altar_pair_is_compiler_eligible():
    variant = {
        "id": "curriculum-gravecrawler-altar",
        "uses": [
            {"card": {"name": "Gravecrawler"}},
            {"card": {"name": "Phyrexian Altar"}},
        ],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    cards = {}
    for name in ("Gravecrawler", "Phyrexian Altar"):
        row = REAL_ORACLE_CURRICULUM[name]
        sem = compile_card(
            f"oracle:{name.lower().replace(' ', '-')}",
            row.name,
            row.oracle_text,
            row.types,
        )
        cards[row.name.casefold()] = sem
    report = evaluate_reference_subset([variant], cards_by_name=cards)
    assert report.counts.eligible >= 1
    assert report.counts.compiler_unsupported == 0
