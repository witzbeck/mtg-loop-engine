"""Claim-bound proof_hash contracts (ADR 0009)."""

from __future__ import annotations

from mtg_loop_engine.config import EngineConfig
from mtg_loop_engine.corpus import all_gold_core
from mtg_loop_engine.proofs.claim import claim_proof_hash
from mtg_loop_engine.proofs.models import VersionIdentity
from mtg_loop_engine.semantics.enums import VerificationStatus
from mtg_loop_engine.semantics.ir import ManaAmount, ManaCost
from mtg_loop_engine.verify.mandatory_recurrence import effective_relevant_state
from mtg_loop_engine.verify.verifier import Verifier
from mtg_loop_engine.state.game import GameState


def _versions() -> VersionIdentity:
    cfg = EngineConfig()
    return VersionIdentity(
        rules_version=cfg.rules_version,
        semantic_schema_version=cfg.semantic_schema_version,
        engine_version=cfg.engine_version,
        proof_schema_version=cfg.proof_schema_version,
        git_sha="deadbeef",
    )


def test_verified_proof_uses_schema_0_2_and_stable_claim_hash():
    witness = all_gold_core()[0]
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.VERIFIED
    assert proof.versions.proof_schema_version == "0.2.0"
    assert len(proof.proof_hash) == 32
    state = GameState.from_spec(witness.initial_state)
    relevant = effective_relevant_state(witness, state)
    expected = claim_proof_hash(
        witness,
        status=VerificationStatus.VERIFIED,
        versions=proof.versions,
        relevant_state=relevant,
    )
    assert proof.proof_hash == expected


def test_git_sha_excluded_from_claim_hash():
    witness = all_gold_core()[0]
    v1 = _versions()
    v2 = v1.model_copy(update={"git_sha": "ffffffffffff"})
    h1 = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=v1
    )
    h2 = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=v2
    )
    assert h1 == h2


def test_reordering_essential_cards_and_assumptions_preserves_hash():
    witness = all_gold_core()[0]
    versions = _versions()
    base = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=versions
    )
    reordered = witness.model_copy(deep=True)
    reordered.essential_cards = list(reversed(reordered.essential_cards))
    reordered.card_semantics = list(reversed(reordered.card_semantics))
    reordered.assumptions = list(reversed(reordered.assumptions))
    reordered.relevant_state = reordered.relevant_state.model_copy(
        update={
            "dimensions": list(reversed(reordered.relevant_state.dimensions)),
        }
    )
    assert (
        claim_proof_hash(
            reordered, status=VerificationStatus.VERIFIED, versions=versions
        )
        == base
    )


def test_changing_card_mana_cost_changes_hash():
    witness = all_gold_core()[0]
    versions = _versions()
    base = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=versions
    )
    mutated = witness.model_copy(deep=True)
    card = mutated.card_semantics[0]
    # Mutate first activated ability cost if present; else bump unsupported.
    for ab in card.abilities:
        costs = getattr(ab, "costs", None)
        if not costs:
            continue
        for cost in costs:
            if isinstance(cost, ManaCost):
                cost.amount = ManaAmount(generic=cost.amount.generic + 1)
                break
        else:
            continue
        break
    else:
        card.unsupported_fragments = list(card.unsupported_fragments) + ["claim-test"]
    assert (
        claim_proof_hash(
            mutated, status=VerificationStatus.VERIFIED, versions=versions
        )
        != base
    )


def test_changing_initial_mana_changes_hash():
    witness = all_gold_core()[0]
    versions = _versions()
    base = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=versions
    )
    mutated = witness.model_copy(deep=True)
    mutated.initial_state = mutated.initial_state.model_copy(
        update={
            "mana": ManaAmount(
                colorless=mutated.initial_state.mana.colorless + 1
            )
        }
    )
    assert (
        claim_proof_hash(
            mutated, status=VerificationStatus.VERIFIED, versions=versions
        )
        != base
    )


def test_changing_recurrence_dimension_changes_hash():
    witness = all_gold_core()[0]
    versions = _versions()
    base = claim_proof_hash(
        witness, status=VerificationStatus.VERIFIED, versions=versions
    )
    mutated = witness.model_copy(deep=True)
    dims = list(mutated.relevant_state.dimensions)
    assert dims, "gold witness must declare recurrence dims"
    first = dims[0].model_copy(deep=True)
    if isinstance(first.value, bool):
        first.value = not first.value
    elif isinstance(first.value, int):
        first.value = first.value + 1
    else:
        first.value = "mutated"
    dims[0] = first
    mutated.relevant_state = mutated.relevant_state.model_copy(
        update={"dimensions": dims}
    )
    assert (
        claim_proof_hash(
            mutated, status=VerificationStatus.VERIFIED, versions=versions
        )
        != base
    )
