"""ABSENT_FROM_REFERENCE labeling for verified discoveries (M5)."""

from pathlib import Path

from mtg_loop_engine.corpus import all_gold_core, gold_core_card_pool
from mtg_loop_engine.corpus.builders import two_card
from mtg_loop_engine.eval.reference_absent import (
    CORPUS_SPELLBOOK_ABSENT,
    candidate_records_from_discovery,
    classify_discovery_vs_reference,
    name_pair_key,
    persist_spellbook_absent_candidates,
)
from mtg_loop_engine.eval.schema import ReferenceStatus
from mtg_loop_engine.eval.store import AdjudicationStore
from mtg_loop_engine.proofs.models import (
    EssentialCardRef,
    InitialStateSpec,
    LoopProof,
    LoopRelevantState,
    LoopWitness,
    RecurrenceResult,
)
from mtg_loop_engine.search.discover import DiscoveryHit, DiscoveryReport, discover_loops
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus


def _hit(a: str, b: str, oid_a: str, oid_b: str) -> DiscoveryHit:
    refs = [
        EssentialCardRef(oracle_id=oid_a, name=a),
        EssentialCardRef(oracle_id=oid_b, name=b),
    ]
    witness = LoopWitness(
        id=f"t_{oid_a}_{oid_b}",
        classification=two_card(essential=refs),
        essential_cards=refs,
        card_semantics=[],
        initial_state=InitialStateSpec(permanents=[]),
        loop_actions=[],
        relevant_state=LoopRelevantState(dimensions=[]),
        expected_outputs=[],
    )
    proof = LoopProof.model_construct(
        status=VerificationStatus.VERIFIED,
        proof_hash=f"hash-{oid_a}-{oid_b}",
        recurrence=RecurrenceResult(ok=True, details=[]),
        semantic_coverage=SemanticCoverage.COMPLETE,
        output_deltas=[],
    )
    return DiscoveryHit(witness=witness, proof=proof, reasons=["test"])


def test_classify_marks_known_pair_in_reference_and_unknown_absent():
    discovery = DiscoveryReport(
        cards=3,
        candidate_pairs=2,
        searched_pairs=2,
        verified=[
            _hit("Gravecrawler", "Phyrexian Altar", "o:gc", "o:altar"),
            _hit("Ashnod's Altar", "Persistent Phoenix", "o:ash", "o:phx"),
        ],
    )
    report = classify_discovery_vs_reference(
        discovery,
        [("Gravecrawler", "Phyrexian Altar")],
    )
    assert report.verified == 2
    assert report.in_reference == 1
    assert report.absent_from_reference == 1
    statuses = {h.reference_status for h in report.hits}
    assert statuses == {
        ReferenceStatus.IN_REFERENCE,
        ReferenceStatus.ABSENT_FROM_REFERENCE,
    }
    absent = next(
        h for h in report.hits if h.reference_status == ReferenceStatus.ABSENT_FROM_REFERENCE
    )
    assert "Phoenix" in absent.right_name or "Phoenix" in absent.left_name
    assert all(h.reference_status != ReferenceStatus.NOVEL for h in report.hits)


def test_name_pair_key_is_casefold_order_independent():
    assert name_pair_key("A", "b") == name_pair_key("B", "a")


def test_gold_pool_extras_label_absent_relative_to_gold_core_pairs():
    """Discoveries beyond gold_core labels are ABSENT_FROM_REFERENCE (not NOVEL)."""
    gold_name_pairs = {
        frozenset(c.name.casefold() for c in witness.essential_cards)
        for witness in all_gold_core()
    }
    discovery = discover_loops(gold_core_card_pool())
    classified = classify_discovery_vs_reference(discovery, gold_name_pairs)
    assert classified.in_reference >= 10
    assert classified.absent_from_reference >= 1
    assert all(h.reference_status != ReferenceStatus.NOVEL for h in classified.hits)


def test_candidate_records_from_discovery_only_absent_default():
    discovery = DiscoveryReport(
        cards=2,
        candidate_pairs=2,
        searched_pairs=2,
        verified=[
            _hit("Gravecrawler", "Phyrexian Altar", "o:gc", "o:altar"),
            _hit("Impact Tremors", "Presence of Gond", "o:tremors", "o:gond"),
        ],
    )
    records = candidate_records_from_discovery(
        discovery,
        [("Gravecrawler", "Phyrexian Altar")],
        oracle_text={
            "o:tremors": "Whenever a creature you control enters, deal 1.",
            "o:gond": 'Enchanted creature has "{T}: Create a token."',
        },
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.corpus == CORPUS_SPELLBOOK_ABSENT
    assert rec.reference_status == ReferenceStatus.ABSENT_FROM_REFERENCE
    assert rec.left_oracle_text
    assert "Tremors" in rec.left_name or "Tremors" in rec.right_name
    assert "Gond" in rec.left_name or "Gond" in rec.right_name


def test_persist_spellbook_absent_candidates_roundtrip(tmp_path: Path):
    gold_name_pairs = {
        frozenset(c.name.casefold() for c in witness.essential_cards)
        for witness in all_gold_core()
    }
    discovery = discover_loops(gold_core_card_pool())
    records = candidate_records_from_discovery(discovery, gold_name_pairs)
    assert records, "expected at least one gold-pool absent for persist contract"
    sample = records[:1]
    db = tmp_path / "adj.duckdb"
    jsonl = tmp_path / "spellbook_absent.jsonl"
    store = AdjudicationStore(db)
    try:
        persist_spellbook_absent_candidates(sample, store, jsonl_path=jsonl)
        loaded = store.list_candidates(corpus=CORPUS_SPELLBOOK_ABSENT)
        assert len(loaded) == 1
        assert loaded[0].candidate_id == sample[0].candidate_id
        assert loaded[0].reference_status == ReferenceStatus.ABSENT_FROM_REFERENCE
    finally:
        store.close()
    assert jsonl.exists()
    line = jsonl.read_text(encoding="utf-8").strip().splitlines()[0]
    assert CORPUS_SPELLBOOK_ABSENT in line
    assert ReferenceStatus.NOVEL.value not in line
