"""Reference-recovery and adjudicated-precision reports."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from mtg_loop_engine.eval.schema import (
    AdjudicationClass,
    AdjudicationRecord,
    CandidateRecord,
    FailureStage,
)


class RecoveryCounts(BaseModel):
    selected: int = 0
    compiled: int = 0
    supported: int = 0
    eligible: int = 0
    rediscovered: int = 0
    join_miss: int = 0
    search_miss: int = 0
    verifier_rejection: int = 0
    classification_mismatch: int = 0
    compiler_unsupported: int = 0

    @property
    def recall_eligible(self) -> float:
        if self.eligible == 0:
            return 0.0
        return self.rediscovered / self.eligible


class RecoveryRow(BaseModel):
    variant_id: str
    names: list[str]
    stage: FailureStage
    detail: str = ""


class RecoveryReport(BaseModel):
    counts: RecoveryCounts = Field(default_factory=RecoveryCounts)
    rows: list[RecoveryRow] = Field(default_factory=list)
    notes: str = (
        "Recall is among eligible/supported entries only. "
        "Spellbook absence is not a false positive."
    )


class PrecisionReport(BaseModel):
    adjudicated: int = 0
    valid: int = 0
    by_class: dict[str, int] = Field(default_factory=dict)
    skipped: int = 0

    @property
    def precision(self) -> float | None:
        if self.adjudicated == 0:
            return None
        return self.valid / self.adjudicated


VALID_CLASSES = {
    AdjudicationClass.VALID_STRICT_TWO_CARD,
    AdjudicationClass.VALID_GENERIC_PREREQUISITE,
}


def precision_from_records(
    candidates: list[CandidateRecord],
    adjudications: dict[str, AdjudicationRecord],
) -> PrecisionReport:
    by_class: Counter[str] = Counter()
    valid = 0
    adjudicated = 0
    skipped = 0
    for candidate in candidates:
        adj = adjudications.get(candidate.candidate_id)
        if adj is None:
            continue
        if adj.skipped:
            skipped += 1
            continue
        adjudicated += 1
        by_class[adj.adjudication.value] += 1
        if adj.adjudication in VALID_CLASSES:
            valid += 1
    return PrecisionReport(
        adjudicated=adjudicated,
        valid=valid,
        by_class=dict(by_class),
        skipped=skipped,
    )
