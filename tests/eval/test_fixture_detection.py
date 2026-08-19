"""Tests for fixture detection and its effect on precision metrics."""

from __future__ import annotations

import pytest

from mtg_loop_engine.eval.gold_extras import (
    FIXTURE_ORACLE_IDS,
    GOLD_EXTRA_ADJUDICATIONS,
    _pair_has_fixture,
)
from mtg_loop_engine.eval.schema import AdjudicationClass
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


# ---------------------------------------------------------------------------
# OracleFixture.is_fixture flag
# ---------------------------------------------------------------------------


KNOWN_FIXTURES = {
    "oracle:suicidal-phoenix",
    "oracle:etb-ping",
    "oracle:self-untap-tapper",
    "oracle:token-tapper",
    "oracle:token-breeder",
}

KNOWN_REAL = {
    "oracle:basalt-monolith",
    "oracle:phyrexian-altar",
    "oracle:gravecrawler",
    "oracle:phoenix",
    "oracle:reassembling-skeleton",
    "oracle:ashnods-altar",
    "oracle:viscera-seer",
    "oracle:soul-warden",
    "oracle:intruder-alarm",
}


def test_known_fixture_ids_are_flagged():
    for oid in KNOWN_FIXTURES:
        fixture = GOLD_ORACLE_FIXTURES.get(oid)
        assert fixture is not None, f"{oid} not in GOLD_ORACLE_FIXTURES"
        assert fixture.is_fixture, f"{oid} should have is_fixture=True"


def test_known_real_ids_are_not_flagged():
    for oid in KNOWN_REAL:
        fixture = GOLD_ORACLE_FIXTURES.get(oid)
        assert fixture is not None, f"{oid} not in GOLD_ORACLE_FIXTURES"
        assert not fixture.is_fixture, f"{oid} should have is_fixture=False"


def test_fixture_oracle_ids_set_matches_known():
    assert KNOWN_FIXTURES == FIXTURE_ORACLE_IDS


# ---------------------------------------------------------------------------
# _pair_has_fixture helper
# ---------------------------------------------------------------------------


def test_pair_has_fixture_when_one_is_fake():
    assert _pair_has_fixture("oracle:suicidal-phoenix", "oracle:phyrexian-altar")


def test_pair_has_fixture_when_both_are_fake():
    assert _pair_has_fixture("oracle:suicidal-phoenix", "oracle:etb-ping")


def test_pair_has_no_fixture_when_both_real():
    assert not _pair_has_fixture("oracle:phyrexian-altar", "oracle:gravecrawler")


# ---------------------------------------------------------------------------
# GOLD_EXTRA_ADJUDICATIONS: fixture pairs labeled correctly
# ---------------------------------------------------------------------------


def test_all_fixture_pairs_labelled_invalid():
    for pair, (cls, notes) in GOLD_EXTRA_ADJUDICATIONS.items():
        ids = list(pair)
        if _pair_has_fixture(ids[0], ids[1]):
            assert cls == AdjudicationClass.INVALID_CANDIDATE_DATA, (
                f"Fixture pair {pair} has class {cls!r} instead of INVALID_CANDIDATE_DATA"
            )


def test_no_real_pair_labelled_invalid():
    for pair, (cls, _) in GOLD_EXTRA_ADJUDICATIONS.items():
        ids = list(pair)
        if not _pair_has_fixture(ids[0], ids[1]):
            assert cls != AdjudicationClass.INVALID_CANDIDATE_DATA, (
                f"Real pair {pair} should not be INVALID_CANDIDATE_DATA"
            )


# ---------------------------------------------------------------------------
# Precision report excludes fixture pairs
# ---------------------------------------------------------------------------


def test_precision_report_excludes_fixture_pairs():
    """precision_from_records should never count INVALID_CANDIDATE_DATA in denominator."""
    from datetime import datetime, timezone

    from mtg_loop_engine.eval.metrics import precision_from_records
    from mtg_loop_engine.eval.schema import (
        AdjudicationRecord,
        CandidateRecord,
        ReferenceStatus,
    )
    from mtg_loop_engine.corpus import all_gold_core
    from mtg_loop_engine.verify.verifier import Verifier

    # Build two minimal CandidateRecord stubs from gold_core witnesses
    verifier = Verifier()
    witnesses = all_gold_core()
    w = witnesses[0]
    proof = verifier.verify(w)
    left, right = sorted(w.essential_cards, key=lambda c: c.oracle_id)
    cid = f"{left.oracle_id}__{right.oracle_id}::testhash"

    from mtg_loop_engine.eval.schema import PrerequisiteAnalysis
    real_candidate = CandidateRecord(
        candidate_id=cid,
        corpus="test",
        left_id=left.oracle_id,
        right_id=right.oracle_id,
        left_name=left.name,
        right_name=right.name,
        reference_status=ReferenceStatus.IN_REFERENCE,
        witness=w,
        proof=proof,
    )
    invalid_candidate = real_candidate.model_copy(update={
        "candidate_id": "invalid__id::hash",
        "left_id": "oracle:suicidal-phoenix",
    })

    now = datetime.now(timezone.utc)
    adjs = {
        cid: AdjudicationRecord(
            candidate_id=cid,
            adjudication=AdjudicationClass.VALID_STRICT_TWO_CARD,
            proof_hash="testhash",
            engine_version="0.1.0",
            reviewed_at=now,
        ),
        "invalid__id::hash": AdjudicationRecord(
            candidate_id="invalid__id::hash",
            adjudication=AdjudicationClass.INVALID_CANDIDATE_DATA,
            proof_hash="hash",
            engine_version="0.1.0",
            reviewed_at=now,
        ),
    }

    report = precision_from_records([real_candidate, invalid_candidate], adjs)
    # Only the real candidate counts toward adjudicated
    assert report.adjudicated == 1
    assert report.valid == 1
    assert report.precision == 1.0
    # INVALID_CANDIDATE_DATA still appears in by_class for visibility
    assert report.by_class.get("invalid_candidate_data", 0) == 1
