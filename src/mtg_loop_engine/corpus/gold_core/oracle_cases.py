"""Oracle-exact gold_core positives (ADR 0007 Wave 1+).

Loads frozen witness artifacts from ``witnesses/*.json``. Semantics are
recompiled from audited ``ORACLE_EXACT`` fixtures on load — search is never
invoked on this path.
"""

from __future__ import annotations

import json
from pathlib import Path

from mtg_loop_engine.proofs.models import LoopWitness
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES

_WITNESSES_DIR = Path(__file__).resolve().parent / "witnesses"

# Stable load order (Wave 1–2 product gold + Heliod/Ballista re-promotion).
_GOLD_IDS: tuple[str, ...] = (
    "core_guard_gond",
    "core_altar_gravecrawler_live",
    "core_alarm_doomsayer",
    "core_bond_blood",
    "core_basalt_zirda",
    "core_druid_vizier",
    "core_rosie_scurry",
    "core_heliod_ballista",
)

_REQUIRED_ASSUMPTIONS = frozenset(
    {"oracle_exact_gold", "compiled_from_audited_fixture"}
)
_FORBIDDEN_ASSUMPTIONS = frozenset({"discovered_without_pair_labels"})


def _compile(oracle_id: str) -> CardSemantics:
    fix = GOLD_ORACLE_FIXTURES[oracle_id]
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    if report.coverage.value != "complete":
        raise RuntimeError(
            f"{oracle_id} incomplete for gold load: "
            f"{report.semantics.unsupported_fragments}"
        )
    return report.semantics


def _load_artifact(gold_id: str) -> LoopWitness:
    path = _WITNESSES_DIR / f"{gold_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing frozen gold witness: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("id") != gold_id:
        raise ValueError(f"{path.name}: id {payload.get('id')!r} != {gold_id!r}")
    payload.pop("artifact_schema_version", None)
    assumptions = set(payload.get("assumptions") or [])
    missing = _REQUIRED_ASSUMPTIONS - assumptions
    if missing:
        raise ValueError(f"{gold_id}: missing assumptions {sorted(missing)}")
    leaked = assumptions & _FORBIDDEN_ASSUMPTIONS
    if leaked:
        raise ValueError(f"{gold_id}: forbidden assumptions {sorted(leaked)}")
    # Prefer fixture recompile over any embedded semantics (artifacts omit them).
    payload.pop("card_semantics", None)
    essential = payload.get("essential_cards") or []
    if len(essential) != 2:
        raise ValueError(f"{gold_id}: expected exactly two essential cards")
    card_semantics = [_compile(ref["oracle_id"]) for ref in essential]
    payload["card_semantics"] = [c.model_dump(mode="json") for c in card_semantics]
    return LoopWitness.model_validate(payload)


def all_gold_core() -> list[LoopWitness]:
    """Return frozen Oracle-exact gold positives (eight product pairs)."""
    return [_load_artifact(gold_id) for gold_id in _GOLD_IDS]


__all__ = ["all_gold_core"]
