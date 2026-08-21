"""Spellbook-shaped reference recovery on committed sample fixtures."""

from pathlib import Path

from mtg_loop_engine.eval.schema import FailureStage
from mtg_loop_engine.eval.spellbook_eval import (
    evaluate_reference_subset,
    load_variant_jsonl,
)

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "eval"
    / "fixtures"
    / "spellbook_conventional_sample.jsonl"
)


def test_sample_recovers_gold_pairs_and_fails_unsupported():
    report = evaluate_reference_subset(load_variant_jsonl(SAMPLE))
    assert report.counts.selected == 3
    stages = {row.variant_id: row.stage for row in report.rows}
    assert stages["ref-basalt-grounds"] == FailureStage.RECOVERED
    assert stages["ref-alarm-tapper"] == FailureStage.RECOVERED
    assert stages["ref-isochron"] == FailureStage.COMPILER_UNSUPPORTED
    assert report.counts.eligible == 2
    assert report.counts.rediscovered == 2
    assert report.counts.recall_eligible == 1.0


def test_gold_extra_adjudications_cover_discovered_extras():
    from mtg_loop_engine.eval.gold_extras import (
        GOLD_EXTRA_ADJUDICATIONS,
        collect_gold_pool_extras,
    )

    extras = collect_gold_pool_extras()
    keys = {frozenset({r.left_id, r.right_id}) for r in extras}
    assert keys == set(GOLD_EXTRA_ADJUDICATIONS)
    assert len(extras) == 10
