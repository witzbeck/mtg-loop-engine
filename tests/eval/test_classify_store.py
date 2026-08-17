"""Unit tests for M4 prerequisite analysis and adjudication store."""

from pathlib import Path

from mtg_loop_engine.corpus.gold_core.cases import BASALT, PHYREXIAN_ALTAR, TRAINING_GROUNDS
from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.eval.schema import AdjudicationClass, AdjudicationRecord
from mtg_loop_engine.eval.store import AdjudicationStore
from mtg_loop_engine.search.explorer import explore_pair


def test_basalt_altar_is_not_strict_two_card():
    found = explore_pair(BASALT, PHYREXIAN_ALTAR)
    assert found is not None
    analysis = analyze_prerequisites(found.witness)
    assert analysis.essential_functional_count == 1
    assert analysis.strict_two_card is False
    assert found.witness.classification.strict_two_card is False
    assert "oracle:phyrexian-altar" in analysis.unused_oracle_ids


def test_basalt_grounds_is_strict_via_cost_reduction():
    found = explore_pair(BASALT, TRAINING_GROUNDS)
    assert found is not None
    analysis = analyze_prerequisites(found.witness)
    assert analysis.strict_two_card is True
    assert set(analysis.used_oracle_ids) == {
        BASALT.oracle_id,
        TRAINING_GROUNDS.oracle_id,
    }


def test_store_roundtrip(tmp_path: Path):
    from mtg_loop_engine.eval.explain import record_from_hit
    from mtg_loop_engine.eval.schema import ReferenceStatus

    found = explore_pair(BASALT, TRAINING_GROUNDS)
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
            adjudication=AdjudicationClass.VALID_STRICT_TWO_CARD,
            notes="gold pair",
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
    assert adj.adjudication == AdjudicationClass.VALID_STRICT_TWO_CARD
    other.close()
