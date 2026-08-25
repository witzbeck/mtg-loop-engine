"""ABSENT_FROM_REFERENCE labeling for verified discoveries (M5)."""

from mtg_loop_engine.corpus import all_gold_core, gold_core_card_pool
from mtg_loop_engine.eval.reference_absent import (
    classify_discovery_vs_reference,
    name_pair_key,
)
from mtg_loop_engine.eval.schema import ReferenceStatus
from mtg_loop_engine.proofs.models import (
    EssentialCardRef,
    InitialStateSpec,
    LoopProof,
    LoopRelevantState,
    LoopWitness,
)
from mtg_loop_engine.corpus.builders import two_card
from mtg_loop_engine.search.discover import DiscoveryHit, DiscoveryReport, discover_loops
from mtg_loop_engine.semantics.enums import VerificationStatus


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
