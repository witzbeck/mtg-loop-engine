"""Golden proof artifact smoke test."""

import json

from mtg_loop_engine.corpus import all_gold_core
from mtg_loop_engine.proofs.normalize import normalize_proof
from mtg_loop_engine.semantics.enums import ProofKind, VerificationStatus
from mtg_loop_engine.verify.verifier import Verifier


def test_golden_proof_roundtrip():
    witness = all_gold_core()[0]
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED
    payload = proof.model_dump(mode="json")
    assert "proof_hash" in payload
    assert "versions" in payload
    text = json.dumps(payload, sort_keys=True)
    assert witness.id in text
    normalized = normalize_proof(proof)
    assert normalized.kind == ProofKind.NORMALIZED
