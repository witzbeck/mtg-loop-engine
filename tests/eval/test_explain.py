"""Explain narration: typed status lead, not “accepted as” for rejects."""

from mtg_loop_engine.corpus import hard_negatives
from mtg_loop_engine.corpus.gold_core import all_gold_core
from mtg_loop_engine.eval.explain import explain_proof
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.verify.verifier import Verifier


def test_explain_verified_lead_does_not_say_accepted():
    witness = next(w for w in all_gold_core() if w.id == "core_guard_gond")
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED
    lead = explain_proof(witness, proof).splitlines()[0]
    assert "verified" in lead.lower()
    assert "accepted as" not in lead.lower()


def test_explain_reject_lead_uses_status_and_reason():
    witness = hard_negatives()[0]
    proof = Verifier().verify(witness)
    assert proof.status != VerificationStatus.VERIFIED
    text = explain_proof(witness, proof)
    lead = text.splitlines()[0]
    assert "rejected as" in lead
    assert proof.status.value in lead
    assert "accepted as" not in text.lower()
    assert "Compiler coverage (not the reject reason):" in text
    if proof.rejection_reason:
        assert proof.rejection_reason in lead
