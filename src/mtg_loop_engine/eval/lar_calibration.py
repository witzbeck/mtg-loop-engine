"""Load and validate LAR v2 durable calibration cases."""

from __future__ import annotations

import json
from pathlib import Path

from mtg_loop_engine.eval.lar_contracts import CalibrationCase

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CALIBRATION_PATH = _REPO_ROOT / "eval" / "calibration" / "adjudication_cases.jsonl"


def load_calibration_cases(path: Path | None = None) -> list[CalibrationCase]:
    """Parse committed calibration JSONL into validated models."""
    target = path or DEFAULT_CALIBRATION_PATH
    cases: list[CalibrationCase] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        cases.append(CalibrationCase.model_validate_json(stripped))
    return cases


def calibration_case_ids(path: Path | None = None) -> set[str]:
    return {case.case_id for case in load_calibration_cases(path)}
