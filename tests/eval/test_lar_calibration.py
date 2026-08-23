"""Tests for LAR v2 calibration contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtg_loop_engine.eval.lar_calibration import load_calibration_cases
from mtg_loop_engine.eval.lar_contracts import (
    CalibrationCase,
    LarManifestV2,
    PromotionCandidate,
    PromotionKind,
)
from mtg_loop_engine.eval.schema import AdjudicationClass

_CALIBRATION = (
    Path(__file__).resolve().parents[2] / "eval" / "calibration" / "adjudication_cases.jsonl"
)
_PROMOTED_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "eval"
    / "reviews"
    / "promoted"
    / "0001-m4-lar-v1"
    / "manifest.json"
)


def test_calibration_jsonl_parses_and_ids_unique() -> None:
    cases = load_calibration_cases(_CALIBRATION)
    assert cases, "expected at least one calibration case"
    ids = [case.case_id for case in cases]
    assert len(ids) == len(set(ids)), "case_id must be unique"


def test_calibration_expected_classes_are_valid_enum() -> None:
    for case in load_calibration_cases(_CALIBRATION):
        assert isinstance(case.expected_class, AdjudicationClass)


def test_calibration_case_model_roundtrip() -> None:
    sample = CalibrationCase(
        case_id="CC-test",
        kind="canonical",
        expected_class=AdjudicationClass.VALID_STRICT_TWO_CARD,
        summary="roundtrip",
    )
    restored = CalibrationCase.model_validate_json(sample.model_dump_json())
    assert restored == sample


def test_promoted_manifest_v2_shape() -> None:
    manifest = LarManifestV2.model_validate_json(_PROMOTED_MANIFEST.read_text(encoding="utf-8"))
    assert manifest.schema_version == "2"
    assert manifest.engine.git_sha
    assert manifest.review_protocol.name == "loop-adjudication-review"


def test_promotion_candidate_kinds_are_usable() -> None:
    candidate = PromotionCandidate(
        candidate_id="PC-001",
        kind=PromotionKind.CALIBRATION_CASE,
        target="eval/calibration",
        summary="example",
    )
    assert candidate.requires_human_adjudication is True
