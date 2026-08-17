"""Hard negatives must fail with expected typed status."""

import pytest

from mtg_loop_engine.corpus import hard_negatives
from mtg_loop_engine.verify.verifier import Verifier


@pytest.mark.parametrize("witness", hard_negatives(), ids=lambda w: w.id)
def test_hard_negative_status(witness):
    proof = Verifier().verify(witness)
    assert witness.expected_status is not None
    assert proof.status == witness.expected_status, (
        f"{witness.id}: got {proof.status} want {witness.expected_status} "
        f"reason={proof.rejection_reason}"
    )
