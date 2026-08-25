"""Engine configuration knobs (arity, duplicates, Spellbook filter defaults)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """Runtime knobs. Only the two-essential path is exercised in M1."""

    max_essential_cards: int = Field(default=2, ge=1, le=3)
    allow_duplicate_oracle_ids: bool = True
    # Benchmark / Commander-facing views default to distinct names.
    prefer_distinct_oracle_ids_in_benchmarks: bool = True
    # Spellbook conventional filter defaults.
    spellbook_require_zero_templates: bool = True
    spellbook_require_repeatable_feature: bool = True
    rules_version: str = "2026-08-07"
    semantic_schema_version: str = "0.1.0"
    proof_schema_version: str = "0.3.0"
    engine_version: str = "0.1.0"
