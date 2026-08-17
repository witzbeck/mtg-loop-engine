"""gold_core positives must VERIFIED."""

import pytest

from mtg_loop_engine.corpus import all_gold_core
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.verify.verifier import Verifier


@pytest.mark.parametrize("witness", all_gold_core(), ids=lambda w: w.id)
def test_gold_core_verified(witness):
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED, (
        f"{witness.id}: {proof.status} {proof.rejection_reason} {proof.recurrence}"
    )
    assert proof.proof_hash
    assert proof.versions.rules_version
    assert proof.versions.engine_version
    assert proof.versions.proof_schema_version
