"""Tests for corpus provenance (ADR 0007) and precision eligibility."""

from __future__ import annotations

from mtg_loop_engine.eval.gold_extras import (
    FIXTURE_ORACLE_IDS,
    GOLD_EXTRA_ADJUDICATIONS,
    PHYSICS_EXTRA_ADJUDICATIONS,
    _pair_has_fixture,
)
from mtg_loop_engine.eval.schema import AdjudicationClass
from mtg_loop_engine.semantics.enums import Provenance
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.provenance import (
    FROZEN_ORACLE_DIVERGENT_IDS,
    assert_exact_fixture_matches_audit,
    current_divergent_ids,
    current_exact_ids,
    is_precision_eligible_ids,
)


KNOWN_SYNTHETIC = {
    "synthetic:generic-activated-cost-reducer",
    "synthetic:token-tapper",
    "synthetic:etb-ping",
    "synthetic:self-untap-tapper",
    "synthetic:suicidal-phoenix",
    "synthetic:token-breeder",
    "synthetic:persistent-phoenix",
    "synthetic:scaled-gun",
    "synthetic:put-counter-activated",
}

KNOWN_EXACT = {
    "oracle:basalt-monolith",
    "oracle:ashnods-altar",
    "oracle:viscera-seer",
    "oracle:soul-warden",
}

KNOWN_DIVERGENT = {
    "oracle:phyrexian-altar",
    "oracle:gravecrawler",
    "oracle:intruder-alarm",
    "oracle:blood-artist",
    "oracle:reassembling-skeleton",
    "oracle:rest-in-peace",
}


def test_synthetic_provenance_and_ids():
    for oid in KNOWN_SYNTHETIC:
        fixture = GOLD_ORACLE_FIXTURES[oid]
        assert fixture.provenance is Provenance.SYNTHETIC
        assert fixture.is_fixture
        assert oid.startswith("synthetic:")


def test_exact_provenance():
    for oid in KNOWN_EXACT:
        fixture = GOLD_ORACLE_FIXTURES[oid]
        assert fixture.provenance is Provenance.ORACLE_EXACT
        assert not fixture.is_fixture


def test_divergent_provenance():
    for oid in KNOWN_DIVERGENT:
        fixture = GOLD_ORACLE_FIXTURES[oid]
        assert fixture.provenance is Provenance.ORACLE_DIVERGENT


def test_fixture_oracle_ids_match_synthetic():
    assert KNOWN_SYNTHETIC == FIXTURE_ORACLE_IDS
    assert FIXTURE_ORACLE_IDS == {
        oid
        for oid, fx in GOLD_ORACLE_FIXTURES.items()
        if fx.provenance is Provenance.SYNTHETIC
    }


def test_cost_reducer_is_not_training_grounds():
    assert "oracle:training-grounds" not in GOLD_ORACLE_FIXTURES
    reducer = GOLD_ORACLE_FIXTURES["synthetic:generic-activated-cost-reducer"]
    assert reducer.name == "Synthetic Cost Reducer"


def test_pair_has_fixture_when_one_is_synthetic():
    assert _pair_has_fixture("synthetic:suicidal-phoenix", "oracle:phyrexian-altar")


def test_pair_has_no_fixture_when_both_non_synthetic():
    assert not _pair_has_fixture("oracle:phyrexian-altar", "oracle:gravecrawler")


def test_precision_requires_both_exact():
    assert is_precision_eligible_ids("oracle:basalt-monolith", "oracle:ashnods-altar")
    assert not is_precision_eligible_ids(
        "oracle:ashnods-altar", "synthetic:persistent-phoenix"
    )
    assert not is_precision_eligible_ids(
        "oracle:phyrexian-altar", "oracle:reassembling-skeleton"
    )


def test_synthetic_extra_pairs_labelled_invalid():
    assert GOLD_EXTRA_ADJUDICATIONS == {}
    for pair, (cls, _) in PHYSICS_EXTRA_ADJUDICATIONS.items():
        ids = list(pair)
        if _pair_has_fixture(ids[0], ids[1]):
            assert cls == AdjudicationClass.INVALID_CANDIDATE_DATA, pair


def test_divergent_skeleton_altar_still_valid_physics():
    key = frozenset({"oracle:phyrexian-altar", "oracle:reassembling-skeleton"})
    cls, _ = PHYSICS_EXTRA_ADJUDICATIONS[key]
    assert cls == AdjudicationClass.VALID_STRICT_TWO_CARD
    assert not is_precision_eligible_ids(*key)


def test_frozen_divergent_inventory_does_not_grow():
    current = current_divergent_ids()
    assert current <= FROZEN_ORACLE_DIVERGENT_IDS, (
        f"new ORACLE_DIVERGENT ids not in freeze: {current - FROZEN_ORACLE_DIVERGENT_IDS}"
    )


def test_every_exact_fixture_matches_audited_record():
    for oid in current_exact_ids():
        assert_exact_fixture_matches_audit(GOLD_ORACLE_FIXTURES[oid])


def test_physics_and_oracle_pool_selectors():
    from mtg_loop_engine.corpus import (
        gold_core_card_pool,
        oracle_gold_card_pool,
        oracle_gold_compiled_card_pool,
        physics_gold_card_pool,
        physics_gold_compiled_card_pool,
    )

    oracle = {c.oracle_id for c in gold_core_card_pool()}
    physics = {c.oracle_id for c in physics_gold_card_pool()}
    exact_pool = {c.oracle_id for c in oracle_gold_card_pool()}
    # Wave 0: Oracle gold empty; physics holds historical synthetic/divergent suite.
    assert exact_pool == oracle
    assert physics
    assert any(oid.startswith("synthetic:") for oid in physics)
    assert not any(oid.startswith("synthetic:") for oid in oracle)
    assert oracle <= KNOWN_EXACT
    assert {c.oracle_id for c in physics_gold_compiled_card_pool()} == physics
    assert {c.oracle_id for c in oracle_gold_compiled_card_pool()} == exact_pool
    # Physics and Oracle pools are separate after Wave 0 (not aliases).
    assert physics != oracle or (not oracle and physics)

def test_canonicalize_and_is_precision_eligible_pair_alias():
    from mtg_loop_engine.semantics.provenance import (
        canonicalize_text,
        is_precision_eligible_pair,
    )

    assert canonicalize_text("a\r\nb") == "a\nb"
    assert is_precision_eligible_pair(
        "oracle:basalt-monolith", "oracle:ashnods-altar"
    )
