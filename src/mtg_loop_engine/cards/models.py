"""Card snapshot models and helpers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OracleCardRecord(BaseModel):
    oracle_id: str
    name: str
    type_line: str | None = None
    oracle_text: str | None = None
    mana_cost: str | None = None
    cmc: float | None = None
    keywords: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)
