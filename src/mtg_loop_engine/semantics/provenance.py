"""Corpus provenance helpers (ADR 0007).

Centralizes precision eligibility and source-record exactness so eval modules
do not rediscover ``left.provenance == EXACT and right.provenance == EXACT``.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from mtg_loop_engine.semantics.enums import Provenance
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES, OracleFixture

AUDITED_DIR = Path(__file__).resolve().parent / "audited" / "records"

# Rules-relevant fields consumed by compilation / verification today.
# Expand when the compiler begins consuming mana cost, colors, keywords, faces, etc.
RULES_RELEVANT_FIELDS: tuple[str, ...] = (
    "oracle_id",
    "name",
    "oracle_text",
    "types",
    "type_line",
)

# Frozen allowlist: CI rejects any ORACLE_DIVERGENT id not in this set.
# Shrink entries when migrating to SYNTHETIC or ORACLE_EXACT; never grow casually.
FROZEN_ORACLE_DIVERGENT_IDS: frozenset[str] = frozenset(
    {
        "oracle:phyrexian-altar",
        "oracle:gravecrawler",
        "oracle:intruder-alarm",
        "oracle:blood-artist",
        "oracle:reassembling-skeleton",
        "oracle:rest-in-peace",
    }
)


def canonicalize_text(value: str) -> str:
    """Representation-only normalize. Never rewrite game meaning."""
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def canonicalize_source_record(record: dict[str, Any]) -> dict[str, Any]:
    """Canonical form of a rules-relevant source record for equality / hashing."""
    out: dict[str, Any] = {}
    for key in RULES_RELEVANT_FIELDS:
        if key not in record:
            continue
        value = record[key]
        if isinstance(value, str):
            out[key] = canonicalize_text(value)
        elif isinstance(value, list):
            out[key] = [
                canonicalize_text(v) if isinstance(v, str) else v for v in value
            ]
        else:
            out[key] = value
    return out


def fixture_as_source_record(fixture: OracleFixture) -> dict[str, Any]:
    type_line = fixture.type_line or " ".join(fixture.types)
    return {
        "oracle_id": fixture.oracle_id,
        "name": fixture.name,
        "oracle_text": fixture.oracle_text,
        "types": list(fixture.types),
        "type_line": type_line,
    }


def load_audited_record(oracle_id: str) -> dict[str, Any]:
    path = AUDITED_DIR / f"{oracle_id.replace(':', '__')}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing audited Oracle record: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def provenance_of(oracle_id: str) -> Provenance | None:
    fixture = GOLD_ORACLE_FIXTURES.get(oracle_id)
    if fixture is None:
        return None
    return fixture.provenance


def is_precision_eligible_ids(left_id: str, right_id: str) -> bool:
    """Product precision requires both essentials to be ORACLE_EXACT."""
    left = provenance_of(left_id)
    right = provenance_of(right_id)
    return left is Provenance.ORACLE_EXACT and right is Provenance.ORACLE_EXACT


def is_precision_eligible_pair(left_id: str, right_id: str) -> bool:
    return is_precision_eligible_ids(left_id, right_id)


def current_divergent_ids() -> frozenset[str]:
    return frozenset(
        oid
        for oid, fx in GOLD_ORACLE_FIXTURES.items()
        if fx.provenance is Provenance.ORACLE_DIVERGENT
    )


def current_exact_ids() -> frozenset[str]:
    return frozenset(
        oid
        for oid, fx in GOLD_ORACLE_FIXTURES.items()
        if fx.provenance is Provenance.ORACLE_EXACT
    )


def assert_exact_fixture_matches_audit(fixture: OracleFixture) -> None:
    if fixture.provenance is not Provenance.ORACLE_EXACT:
        raise AssertionError(f"{fixture.oracle_id} is not ORACLE_EXACT")
    audited = canonicalize_source_record(load_audited_record(fixture.oracle_id))
    live = canonicalize_source_record(fixture_as_source_record(fixture))
    if audited != live:
        raise AssertionError(
            f"ORACLE_EXACT mismatch for {fixture.oracle_id}:\n"
            f"  audited={audited!r}\n"
            f"  fixture={live!r}"
        )
