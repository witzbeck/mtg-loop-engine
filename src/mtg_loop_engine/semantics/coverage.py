"""Compiler coverage metrics and per-fragment results."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import Ability, CardSemantics


class FragmentResult(BaseModel):
    text: str
    supported: bool
    pattern_id: str | None = None
    ability: Ability | None = None
    note: str | None = None


class CompileReport(BaseModel):
    oracle_id: str
    name: str
    fragments: list[FragmentResult] = Field(default_factory=list)
    semantics: CardSemantics
    coverage: SemanticCoverage

    @property
    def supported_count(self) -> int:
        return sum(1 for f in self.fragments if f.supported)

    @property
    def fragment_count(self) -> int:
        return len(self.fragments)


class CoverageMetrics(BaseModel):
    """Aggregate semantic coverage over a corpus of compile reports."""

    cards: int = 0
    fragments_total: int = 0
    fragments_supported: int = 0
    cards_complete: int = 0
    cards_partial_irrelevant: int = 0
    cards_partial_relevant: int = 0

    @property
    def fragment_coverage(self) -> float:
        if self.fragments_total == 0:
            return 1.0
        return self.fragments_supported / self.fragments_total

    @property
    def card_complete_rate(self) -> float:
        if self.cards == 0:
            return 1.0
        return self.cards_complete / self.cards


def aggregate_coverage(reports: list[CompileReport]) -> CoverageMetrics:
    metrics = CoverageMetrics(cards=len(reports))
    for report in reports:
        metrics.fragments_total += report.fragment_count
        metrics.fragments_supported += report.supported_count
        if report.coverage == SemanticCoverage.COMPLETE:
            metrics.cards_complete += 1
        elif report.coverage == SemanticCoverage.PARTIAL_IRRELEVANT_TO_PROOF:
            metrics.cards_partial_irrelevant += 1
        else:
            metrics.cards_partial_relevant += 1
    return metrics
