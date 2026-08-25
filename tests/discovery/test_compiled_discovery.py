"""M3.5 seam: physics Oracle fixtures → compiler → blind discovery → verifier."""

from mtg_loop_engine.corpus import (
    gold_core_compiled_card_pool,
    gold_core_pair_keys,
    physics_gold_compiled_card_pool,
    physics_gold_pair_keys,
)
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def test_compiled_physics_pool_fixture_cards_are_complete():
    """Cards that have GOLD_ORACLE_FIXTURES entries compile COMPLETE."""
    pool = physics_gold_compiled_card_pool()
    fixture_ids = {c.oracle_id for c in pool if c.oracle_id in GOLD_ORACLE_FIXTURES}
    assert fixture_ids
    for card in pool:
        if card.oracle_id not in GOLD_ORACLE_FIXTURES:
            continue
        assert card.coverage == SemanticCoverage.COMPLETE
        assert not card.unsupported_fragments


def test_blind_discovery_rediscovers_physics_from_compiled_ir():
    gold = physics_gold_pair_keys()
    report = discover_loops(physics_gold_compiled_card_pool(), max_depth=6)
    missing = gold - report.verified_pairs
    assert not missing, (
        f"compiled-IR discovery missed {len(missing)}/{len(gold)} physics pairs: "
        f"{missing}; found {report.verified_pairs}"
    )
    for hit in report.verified:
        assert hit.proof.status == VerificationStatus.VERIFIED
        assert "discovered_without_pair_labels" in hit.witness.assumptions


def test_oracle_compiled_pool_matches_gold_core_keys():
    pool = gold_core_compiled_card_pool()
    assert {c.oracle_id for c in pool} == {
        oid for pair in gold_core_pair_keys() for oid in pair
    }
