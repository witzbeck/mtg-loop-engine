"""Canonical claim payload and proof_hash (ADR 0009).

``LoopProof.proof_hash`` is a claim hash: it binds the epistemic content of the
verification attempt so adjudications keyed by ``…::proof_hash`` cannot silently
attach to a materially different claim.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from mtg_loop_engine.proofs.models import LoopRelevantState, LoopWitness, VersionIdentity
from mtg_loop_engine.semantics.enums import VerificationStatus


def _dump(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model


def _sorted_by_oracle_id(items: list[Any]) -> list[Any]:
    return sorted(items, key=lambda x: getattr(x, "oracle_id", str(x)))


def build_claim_payload(
    witness: LoopWitness,
    *,
    status: VerificationStatus,
    versions: VersionIdentity,
    rejection_reason: str | None = None,
    relevant_state: LoopRelevantState | None = None,
) -> dict[str, Any]:
    """Stable claim dict. Excludes git_sha, timestamps, and other volatiles."""
    relevant = relevant_state if relevant_state is not None else witness.relevant_state
    dims = sorted(relevant.dimensions, key=lambda d: d.path)
    prereqs = sorted(
        witness.prerequisites,
        key=lambda p: (p.kind, p.description),
    )
    return {
        "proof_schema_version": versions.proof_schema_version,
        "engine_version": versions.engine_version,
        "rules_version": versions.rules_version,
        "semantic_schema_version": versions.semantic_schema_version,
        "status": status.value,
        "rejection_reason": rejection_reason,
        "witness_id": witness.id,
        "deterministic": witness.deterministic,
        "semantic_coverage": witness.semantic_coverage.value,
        "essential_cards": [
            _dump(c) for c in _sorted_by_oracle_id(list(witness.essential_cards))
        ],
        "card_semantics": [
            _dump(c) for c in _sorted_by_oracle_id(list(witness.card_semantics))
        ],
        "classification": _dump(witness.classification),
        "initial_state": _dump(witness.initial_state),
        "setup_actions": [_dump(a) for a in witness.setup_actions],
        "loop_actions": [_dump(a) for a in witness.loop_actions],
        "relevant_state": {
            "dimensions": [_dump(d) for d in dims],
        },
        "expected_outputs": [_dump(o) for o in witness.expected_outputs],
        "prerequisites": [_dump(p) for p in prereqs],
        "assumptions": sorted(witness.assumptions),
    }


def proof_hash(payload: dict[str, Any]) -> str:
    """SHA-256 truncated to 32 hex chars over canonical JSON."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def claim_proof_hash(
    witness: LoopWitness,
    *,
    status: VerificationStatus,
    versions: VersionIdentity,
    rejection_reason: str | None = None,
    relevant_state: LoopRelevantState | None = None,
) -> str:
    return proof_hash(
        build_claim_payload(
            witness,
            status=status,
            versions=versions,
            rejection_reason=rejection_reason,
            relevant_state=relevant_state,
        )
    )
