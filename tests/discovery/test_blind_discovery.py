"""Blind two-card discovery tests (no gold pair labels on the search path)."""

from mtg_loop_engine.corpus import gold_core_card_pool, gold_core_pair_keys
from mtg_loop_engine.interactions.capabilities import extract_capabilities, join_reasons
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import VerificationStatus


def test_index_joins_cover_gold_pairs():
    pool = gold_core_card_pool()
    index = InteractionIndex(pool)
    joined = {
        frozenset({pair.left_id, pair.right_id}) for pair in index.candidate_pairs()
    }
    missing = gold_core_pair_keys() - joined
    assert not missing, f"join index missed gold pairs: {missing}"


def test_basalt_and_grounds_are_complementary():
    pool = {c.oracle_id: c for c in gold_core_card_pool()}
    basalt = extract_capabilities(pool["oracle:basalt-monolith"])
    grounds = extract_capabilities(pool["oracle:training-grounds"])
    reasons = join_reasons(basalt, grounds) + join_reasons(grounds, basalt)
    assert "cost_reduce" in reasons


def test_blind_discovery_rediscovers_gold_core():
    pool = gold_core_card_pool()
    gold = gold_core_pair_keys()
    report = discover_loops(pool, max_depth=6)
    missing = gold - report.verified_pairs
    assert report.candidate_pairs >= len(gold)
    assert not missing, (
        f"failed to rediscover {len(missing)}/{len(gold)} gold pairs: {missing}; "
        f"found {report.verified_pairs}"
    )
    for hit in report.verified:
        assert hit.proof.status == VerificationStatus.VERIFIED
        assert "discovered_without_pair_labels" in hit.witness.assumptions
