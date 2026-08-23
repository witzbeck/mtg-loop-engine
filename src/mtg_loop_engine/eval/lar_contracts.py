"""LAR v2 contracts: manifest provenance, calibration cases, promotion candidates."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from mtg_loop_engine.eval.schema import AdjudicationClass


class CalibrationCaseKind(StrEnum):
    CANONICAL = "canonical"
    BOUNDARY = "boundary"
    COUNTERFACTUAL = "counterfactual"


class PromotionKind(StrEnum):
    ADJUDICATION_CHANGE = "adjudication_change"
    CALIBRATION_CASE = "calibration_case"
    REGRESSION_TEST = "regression_test"
    COMPILER_CURRICULUM = "compiler_curriculum"
    DOCUMENTATION = "documentation"
    BASELINE_REFRESH = "baseline_refresh"
    ADR_CANDIDATE = "adr_candidate"
    PROMOTED_EVIDENCE = "promoted_evidence"
    NO_ACTION = "no_action"


class BlindCompareOutcome(StrEnum):
    AGREE_HIGH_CONFIDENCE = "agree_high_confidence"
    AGREE_LOW_CONFIDENCE = "agree_low_confidence"
    DISAGREE = "disagree"
    TAXONOMY_AMBIGUOUS = "taxonomy_ambiguous"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class LarEngineProvenance(BaseModel):
    git_sha: str
    dirty: bool = False


class LarReviewProtocol(BaseModel):
    name: str = "loop-adjudication-review"
    version: str = "2"
    skill_sha: str | None = None
    blinded_pair_review: bool = False
    adversarial_challenge: bool = False


class LarEvaluatorProvenance(BaseModel):
    model_identifier: str | None = None


class LarTaxonomyProvenance(BaseModel):
    source: str = "docs/ADJUDICATION.md"
    sha256: str | None = None


class LarDatasetProvenance(BaseModel):
    adjudications_sha256: str | None = None
    calibration_sha256: str | None = None
    gold_core_sha256: str | None = None
    oracle_snapshot_id: str | None = None


class LarManifestV2(BaseModel):
    """Semantic provenance for an ephemeral run under data/eval/lar/runs/."""

    schema_version: str = "2"
    run_id: str
    started_at: datetime
    engine: LarEngineProvenance
    review_protocol: LarReviewProtocol = Field(default_factory=LarReviewProtocol)
    evaluator: LarEvaluatorProvenance = Field(default_factory=LarEvaluatorProvenance)
    taxonomy: LarTaxonomyProvenance = Field(default_factory=LarTaxonomyProvenance)
    datasets: LarDatasetProvenance = Field(default_factory=LarDatasetProvenance)
    pytest_passed: bool | None = None
    notes: str = ""


class CalibrationCase(BaseModel):
    """Curated taxonomy exercise — not an observed adjudication row."""

    case_id: str
    kind: CalibrationCaseKind
    expected_class: AdjudicationClass
    summary: str
    gold_core_witness_id: str | None = None
    pair_scope_id: str | None = None
    boundary_with: str | None = None
    notes: str = ""
    source_run: str | None = None


class PromotionCandidate(BaseModel):
    """Proposed durable knowledge — never auto-committed by LAR execution."""

    candidate_id: str
    kind: PromotionKind
    target: str
    summary: str
    evidence_paths: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    requires_human_adjudication: bool = True
    suspected_layer: str | None = None
    recommended_action: str = ""


class LarKnowledgeChanges(BaseModel):
    """Information-gain summary for synthesis — not an aggregate score."""

    new_adjudication_cases: int = 0
    changed_adjudications: int = 0
    new_calibration_cases: int = 0
    new_regression_tests: int = 0
    new_counterfactual_negatives: int = 0
    documentation_corrections: int = 0
    adr_candidates: int = 0
    certified_baseline_changes: int = 0
    unresolved_escalations: int = 0


class LarCoverageReport(BaseModel):
    adjudication_classes_represented: str = "0/8"
    classes_with_boundary_examples: str = "0/8"
    known_mechanic_families_tested: int = 0
    held_out_families_tested: int = 0
    real_card_blind_adjudications: int = 0
    fixture_only_adjudications: int = 0
    counterfactual_negatives_tested: int = 0
