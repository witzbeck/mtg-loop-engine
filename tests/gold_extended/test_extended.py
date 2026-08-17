"""gold_extended may be UNSUPPORTED without failing M1 gate."""

from mtg_loop_engine.corpus import gold_extended_catalog
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.verify.verifier import Verifier


def test_extended_unsupported():
    catalog = gold_extended_catalog()
    assert len(catalog) >= 15
    v = Verifier()
    for w in catalog:
        proof = v.verify(w)
        assert proof.status in {
            VerificationStatus.UNSUPPORTED_SEMANTICS,
            VerificationStatus.UNSUPPORTED_RULE,
        }
