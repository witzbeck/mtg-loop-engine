"""M4 evaluation records and adjudication vocabulary."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from mtg_loop_engine.proofs.models import LoopProof, LoopWitness


class AdjudicationClass(StrEnum):
    VALID_STRICT_TWO_CARD = "valid_strict_two_card"
    VALID_GENERIC_PREREQUISITE = "valid_generic_prerequisite"
    FUNCTIONAL_EXTERNAL_REQUIREMENT = "functional_external_requirement"
    UNJUSTIFIED_INITIAL_STATE = "unjustified_initial_state"
    RULES_OR_SEMANTICS_FALSE_POSITIVE = "rules_or_semantics_false_positive"
    DUPLICATE_OR_EQUIVALENT_INTERACTION = "duplicate_or_equivalent_interaction"
    # Cards interact productively but cannot recur (finite combo mislabeled as loop).
    FINITE_INTERACTION_MISCLASSIFIED_AS_LOOP = "finite_interaction_misclassified_as_loop"
    INVALID_CANDIDATE_DATA = "invalid_candidate_data"
    NEEDS_RULES_RESEARCH = "needs_rules_research"


class AdjudicationFailureReason(StrEnum):
    """Optional diagnostic codes under an adjudication class (v1: finite / recurrence)."""

    RECURRENCE_FAILURE = "recurrence_failure"
    RESOURCE_NOT_RESTORED = "resource_not_restored"
    PARTICIPANT_FAILURE = "participant_failure"
    ILLEGAL_EXECUTION = "illegal_execution"


class ReferenceStatus(StrEnum):
    IN_REFERENCE = "in_reference"
    ABSENT_FROM_REFERENCE = "absent_from_reference"
    NOVEL = "novel"


class AssumptionKind(StrEnum):
    INTRINSIC = "intrinsic"
    GENERIC_PREREQUISITE = "generic_prerequisite"
    FUNCTIONAL_EXTERNAL = "functional_external"
    UNSUPPORTED = "unsupported"
    UNJUSTIFIED = "unjustified"


class FailureStage(StrEnum):
    COMPILER_UNSUPPORTED = "compiler_unsupported"
    CANDIDATE_JOIN_MISS = "candidate_join_miss"
    SEARCH_MISS = "search_miss"
    VERIFIER_REJECTION = "verifier_rejection"
    PREREQUISITE_MISMATCH = "prerequisite_classification_mismatch"
    RECOVERED = "recovered"
    NOT_ELIGIBLE = "not_eligible"


class StateAssumption(BaseModel):
    kind: AssumptionKind
    description: str
    object_id: str | None = None
    oracle_id: str | None = None


class PrerequisiteAnalysis(BaseModel):
    used_oracle_ids: list[str] = Field(default_factory=list)
    unused_oracle_ids: list[str] = Field(default_factory=list)
    assumptions: list[StateAssumption] = Field(default_factory=list)
    generic_prerequisites: list[str] = Field(default_factory=list)
    functional_external_requirements: list[str] = Field(default_factory=list)
    essential_functional_count: int = 0
    strict_two_card: bool = False
    notes: list[str] = Field(default_factory=list)


class CandidateRecord(BaseModel):
    """One accepted discovery queued for review. Search never sees pair labels."""

    candidate_id: str
    corpus: str
    left_id: str
    right_id: str
    left_name: str
    right_name: str
    left_oracle_text: str = ""
    right_oracle_text: str = ""
    join_reasons: list[str] = Field(default_factory=list)
    reference_status: ReferenceStatus = ReferenceStatus.ABSENT_FROM_REFERENCE
    analysis: PrerequisiteAnalysis = Field(default_factory=PrerequisiteAnalysis)
    explanation: str = ""
    witness: LoopWitness
    proof: LoopProof
    engine_version: str = "0.1.0"
    oracle_snapshot_hash: str | None = None
    spellbook_snapshot_hash: str | None = None


class AdjudicationRecord(BaseModel):
    candidate_id: str
    adjudication: AdjudicationClass
    notes: str = ""
    failure_reasons: list[AdjudicationFailureReason] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    proof_hash: str
    engine_version: str
    oracle_snapshot_hash: str | None = None
    skipped: bool = False
