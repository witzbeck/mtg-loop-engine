"""gold_extended may be UNSUPPORTED without failing M1 gate."""

from mtg_loop_engine.corpus import gold_extended_catalog
from mtg_loop_engine.corpus.gold_extended import oracle_gap_catalog
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


def test_oracle_gaps_document_wave3_blockers():
    gaps = oracle_gap_catalog()
    ids = {g.proposed_gold_id for g in gaps}
    assert "core_saffi_champion" in ids
    assert "core_mikaeus_triskelion" in ids
    assert "core_heliod_ballista" not in ids
    for g in gaps:
        assert g.blockers
