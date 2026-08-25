"""Claim consequence derivation contracts (ACCUMULATES / REPEATABLE_EVENT / LETHAL)."""

from __future__ import annotations

from mtg_loop_engine.corpus import all_gold_core
from mtg_loop_engine.proofs.consequence import (
    claim_consequence_mismatch,
    derive_claim_consequence,
    has_beneficial_accumulation,
)
from mtg_loop_engine.proofs.models import NetStateDelta
from mtg_loop_engine.semantics.enums import Consequence, VerificationStatus
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.verify.verifier import Verifier


def test_derive_accumulates_from_mana():
    net = NetStateDelta(mana=ManaAmount(green=1))
    assert has_beneficial_accumulation(net)
    assert (
        derive_claim_consequence(net, gross_event_ok=True) is Consequence.ACCUMULATES
    )


def test_derive_accumulates_from_tokens():
    net = NetStateDelta(creature_tokens=1)
    assert (
        derive_claim_consequence(net, gross_event_ok=True) is Consequence.ACCUMULATES
    )


def test_derive_lethal_from_opponent_life_loss():
    """Recurrent −1 life/iteration is unbounded; LETHAL beats ACCUMULATES (life_you)."""
    net = NetStateDelta(life_you=1, life_opponent=-1)
    assert derive_claim_consequence(net, gross_event_ok=True) is Consequence.LETHAL


def test_derive_repeatable_event_when_net_zero():
    net = NetStateDelta()
    assert (
        derive_claim_consequence(net, gross_event_ok=True)
        is Consequence.REPEATABLE_EVENT
    )


def test_derive_other_when_net_zero_without_gross_event():
    net = NetStateDelta()
    assert derive_claim_consequence(net, gross_event_ok=False) is Consequence.OTHER


def test_mismatch_rejects_wrong_label():
    derived = Consequence.REPEATABLE_EVENT
    msg = claim_consequence_mismatch(derived, Consequence.LETHAL)
    assert msg is not None
    assert "lethal" in msg and "repeatable_event" in msg


def test_mismatch_none_expected_ok():
    assert claim_consequence_mismatch(Consequence.ACCUMULATES, None) is None


def test_gold_claim_consequences_match_derivation():
    """Frozen gold labels must agree with derived consequence."""
    v = Verifier()
    for w in all_gold_core():
        proof = v.verify(w)
        assert proof.status is VerificationStatus.VERIFIED, w.id
        assert proof.claim_consequence is not None, w.id
        assert w.expected_claim_consequence is not None, w.id
        assert proof.claim_consequence is w.expected_claim_consequence, (
            w.id,
            proof.claim_consequence,
            w.expected_claim_consequence,
        )


def test_wrong_claim_label_on_gold_witness_rejects():
    """Adversarial: stamp LETHAL on an ACCUMULATES gold → NOT_A_LOOP."""
    base = next(w for w in all_gold_core() if w.id == "core_guard_gond")
    adversarial = base.model_copy(
        update={"expected_claim_consequence": Consequence.LETHAL}
    )
    proof = Verifier().verify(adversarial)
    assert proof.status is VerificationStatus.NOT_A_LOOP
    assert proof.rejection_reason is not None
    assert "claim consequence mismatch" in proof.rejection_reason
