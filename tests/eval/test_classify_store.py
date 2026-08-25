"""Unit tests for M4 prerequisite analysis and adjudication store."""

from pathlib import Path

import pytest

from mtg_loop_engine.corpus.gold_core.cases import (
    ASHNOD,
    BASALT,
    GRAVECRAWLER,
    INTRUDER_ALARM,
    PHYREXIAN_ALTAR,
    SKELETON,
    SYNTHETIC_COST_REDUCER,
)
from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.eval.schema import AdjudicationClass, AdjudicationRecord
from mtg_loop_engine.eval.store import AdjudicationStore
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.ir import CardSemantics

# Real-card pairs adjudicated duplicate_or_equivalent_interaction because one
# essential never acted (Basalt self-untap). Must not be accepted after the gate.
BYSTANDER_REGRESSION_PAIRS: list[tuple[CardSemantics, CardSemantics]] = [
    (BASALT, ASHNOD),
    (BASALT, GRAVECRAWLER),
    (BASALT, INTRUDER_ALARM),
    (BASALT, PHYREXIAN_ALTAR),
    (BASALT, SKELETON),
]


@pytest.mark.parametrize(
    "left,right",
    BYSTANDER_REGRESSION_PAIRS,
    ids=[
        "basalt-ashnod",
        "basalt-gravecrawler",
        "basalt-intruder-alarm",
        "basalt-phyrexian-altar",
        "basalt-skeleton",
    ],
)
def test_bystander_pairs_are_not_accepted(left: CardSemantics, right: CardSemantics):
    assert explore_pair(left, right) is None


def test_basalt_grounds_is_strict_via_cost_reduction():
    found = explore_pair(BASALT, SYNTHETIC_COST_REDUCER)
    assert found is not None
    analysis = analyze_prerequisites(found.witness)
    assert analysis.strict_two_card is True
    assert found.witness.classification.strict_two_card is True
    assert set(analysis.used_oracle_ids) == {
        BASALT.oracle_id,
        SYNTHETIC_COST_REDUCER.oracle_id,
    }


def test_store_roundtrip(tmp_path: Path):
    from mtg_loop_engine.eval.explain import record_from_hit
    from mtg_loop_engine.eval.schema import AdjudicationFailureReason, ReferenceStatus

    found = explore_pair(BASALT, SYNTHETIC_COST_REDUCER)
    assert found is not None
    record = record_from_hit(
        witness=found.witness,
        proof=found.proof,
        reasons=["cost_reduce"],
        corpus="test",
        reference_status=ReferenceStatus.ABSENT_FROM_REFERENCE,
    )
    store = AdjudicationStore(tmp_path / "adj.duckdb")
    store.upsert_candidate(record)
    store.save_adjudication(
        AdjudicationRecord(
            candidate_id=record.candidate_id,
            adjudication=AdjudicationClass.FINITE_INTERACTION_MISCLASSIFIED_AS_LOOP,
            notes="example finite",
            failure_reasons=[
                AdjudicationFailureReason.RECURRENCE_FAILURE,
                AdjudicationFailureReason.RESOURCE_NOT_RESTORED,
            ],
            proof_hash=record.proof.proof_hash,
            engine_version=record.engine_version,
        )
    )
    jsonl = tmp_path / "out.jsonl"
    store.export_jsonl(jsonl)
    store.close()

    other = AdjudicationStore(tmp_path / "other.duckdb")
    count = other.import_jsonl(jsonl)
    assert count == 1
    loaded = other.get_candidate(record.candidate_id)
    assert loaded is not None
    assert loaded.left_name == "Basalt Monolith"
    adj = other.get_adjudication(record.candidate_id)
    assert adj is not None
    assert adj.adjudication == AdjudicationClass.FINITE_INTERACTION_MISCLASSIFIED_AS_LOOP
    assert adj.failure_reasons == [
        AdjudicationFailureReason.RECURRENCE_FAILURE,
        AdjudicationFailureReason.RESOURCE_NOT_RESTORED,
    ]
    other.close()


def test_store_close_is_idempotent(tmp_path: Path):
    store = AdjudicationStore(tmp_path / "adj.duckdb")
    store.close()
    store.close()


def test_store_context_manager_closes(tmp_path: Path):
    path = tmp_path / "adj.duckdb"
    with AdjudicationStore(path) as store:
        assert store.list_candidates() == []
    # Re-open after context exit proves the file lock was released.
    again = AdjudicationStore(path)
    again.close()


def test_lock_holder_pid_parses_duckdb_message():
    from mtg_loop_engine.eval.store import lock_holder_pid

    msg = (
        'Could not set lock on file "/tmp/x.duckdb": Conflicting lock is held in '
        "/usr/bin/python3.13 (PID 992165) by user fr333y3d3a"
    )
    assert lock_holder_pid(msg) == 992165
    assert lock_holder_pid("unrelated") is None


def test_second_open_while_locked_raises_duckdb_lock_error(tmp_path: Path):
    """Cross-process lock (same-process DuckDB allows multiple connections)."""
    import subprocess
    import sys
    import time

    from mtg_loop_engine.eval.store import DuckDBLockError

    path = tmp_path / "locked.duckdb"
    ready = tmp_path / "ready"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import time\n"
                "from pathlib import Path\n"
                "from mtg_loop_engine.eval.store import AdjudicationStore\n"
                f"s = AdjudicationStore(Path({str(path)!r}))\n"
                f"Path({str(ready)!r}).write_text('1', encoding='utf-8')\n"
                "time.sleep(60)\n"
                "s.close()\n"
            ),
        ],
        cwd=str(Path(__file__).resolve().parents[2]),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 10
        while not ready.exists():
            if holder.poll() is not None:
                raise AssertionError("holder process exited before locking")
            if time.time() > deadline:
                raise AssertionError("timed out waiting for holder lock")
            time.sleep(0.05)
        with pytest.raises(DuckDBLockError, match="Lock holder PID"):
            AdjudicationStore(path)
    finally:
        holder.terminate()
        holder.wait(timeout=10)


def test_queue_treats_skipped_as_reviewed(tmp_path: Path):
    from mtg_loop_engine.eval.explain import record_from_hit
    from mtg_loop_engine.eval.schema import ReferenceStatus

    found = explore_pair(BASALT, SYNTHETIC_COST_REDUCER)
    assert found is not None
    record = record_from_hit(
        witness=found.witness,
        proof=found.proof,
        reasons=["cost_reduce"],
        corpus="test",
        reference_status=ReferenceStatus.ABSENT_FROM_REFERENCE,
    )
    store = AdjudicationStore(tmp_path / "adj.duckdb")
    store.upsert_candidate(record)
    assert len(store.queue(reviewed=False)) == 1
    store.save_adjudication(
        AdjudicationRecord(
            candidate_id=record.candidate_id,
            adjudication=AdjudicationClass.NEEDS_RULES_RESEARCH,
            notes="",
            proof_hash=record.proof.proof_hash,
            engine_version=record.engine_version,
            skipped=True,
        )
    )
    assert store.queue(reviewed=False) == []
    assert len(store.queue(reviewed=True)) == 1
    store.close()
