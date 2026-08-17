"""M3.5 seam: gold Oracle fixtures → compiler → blind discovery → verifier."""

from mtg_loop_engine.corpus import (
    gold_core_compiled_card_pool,
    gold_core_pair_keys,
)
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus


def test_compiled_pool_has_complete_coverage():
    pool = gold_core_compiled_card_pool()
    assert {c.oracle_id for c in pool} == {
        oid for pair in gold_core_pair_keys() for oid in pair
    }
    for card in pool:
        assert card.coverage == SemanticCoverage.COMPLETE
        assert not card.unsupported_fragments


def test_blind_discovery_rediscovers_gold_core_from_compiled_ir():
    gold = gold_core_pair_keys()
    report = discover_loops(gold_core_compiled_card_pool(), max_depth=6)
    missing = gold - report.verified_pairs
    assert not missing, (
        f"compiled-IR discovery missed {len(missing)}/{len(gold)} gold pairs: "
        f"{missing}; found {report.verified_pairs}"
    )
    for hit in report.verified:
        assert hit.proof.status == VerificationStatus.VERIFIED
        assert "discovered_without_pair_labels" in hit.witness.assumptions
        for card in hit.witness.card_semantics:
            # Search must have used compiled objects, not gold_core manual IR.
            assert card.coverage == SemanticCoverage.COMPLETE
