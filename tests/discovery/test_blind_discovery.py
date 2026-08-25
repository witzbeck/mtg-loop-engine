"""Blind two-card discovery tests (physics fixtures; Oracle gold may be empty)."""

from mtg_loop_engine.corpus import (
    gold_core_card_pool,
    gold_core_pair_keys,
    physics_gold_card_pool,
    physics_gold_pair_keys,
)
from mtg_loop_engine.interactions.capabilities import extract_capabilities, join_reasons
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import VerificationStatus


def test_index_joins_cover_physics_pairs():
    pool = physics_gold_card_pool()
    index = InteractionIndex(pool)
    joined = {
        frozenset({pair.left_id, pair.right_id}) for pair in index.candidate_pairs()
    }
    missing = physics_gold_pair_keys() - joined
    assert not missing, f"join index missed physics pairs: {missing}"


def test_basalt_and_cost_reducer_are_complementary():
    pool = {c.oracle_id: c for c in physics_gold_card_pool()}
    basalt = extract_capabilities(pool["oracle:basalt-monolith"])
    grounds = extract_capabilities(pool["synthetic:generic-activated-cost-reducer"])
    reasons = join_reasons(basalt, grounds) + join_reasons(grounds, basalt)
    assert "cost_reduce" in reasons


def test_blind_discovery_rediscovers_physics_core():
    pool = physics_gold_card_pool()
    gold = physics_gold_pair_keys()
    report = discover_loops(pool, max_depth=6)
    missing = gold - report.verified_pairs
    assert report.candidate_pairs >= len(gold)
    assert not missing, (
        f"failed to rediscover {len(missing)}/{len(gold)} physics pairs: {missing}; "
        f"found {report.verified_pairs}"
    )
    for hit in report.verified:
        assert hit.proof.status == VerificationStatus.VERIFIED
        assert "discovered_without_pair_labels" in hit.witness.assumptions


def test_oracle_gold_discovery_rediscovers_promoted_pairs():
    """Blind rediscovery of frozen gold pair keys (separate from gold load)."""
    pool = gold_core_card_pool()
    gold = gold_core_pair_keys()
    report = discover_loops(pool, max_depth=10)
    missing = gold - report.verified_pairs
    assert gold
    assert not missing, (
        f"failed to rediscover {len(missing)}/{len(gold)} Oracle gold pairs: {missing}"
    )
    for hit in report.verified:
        if frozenset(c.oracle_id for c in hit.witness.essential_cards) in gold:
            assert hit.proof.status == VerificationStatus.VERIFIED
            assert "discovered_without_pair_labels" in hit.witness.assumptions
