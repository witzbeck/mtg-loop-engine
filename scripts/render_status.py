#!/usr/bin/env python3
"""Render or check docs/STATUS.md quantitative section from frozen baselines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.md"
GOLD_BASELINE = ROOT / "eval" / "baseline" / "m4_gold_pool_summary.json"
SPELLBOOK_BASELINE = ROOT / "eval" / "baseline" / "m4_spellbook_recovery_summary.json"

BEGIN = "<!-- BEGIN:GENERATED_FROM_BASELINES -->"
END = "<!-- END:GENERATED_FROM_BASELINES -->"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_by_class(by_class: dict) -> list[str]:
    rows = []
    for key in sorted(by_class):
        rows.append(f"| by_class.{key} | {by_class[key]} |")
    return rows


def render_generated_section(gold: dict, spellbook: dict) -> str:
    counts = spellbook.get("counts", {})
    recall = counts.get("recall_eligible")
    recall_display = "null (no eligible pairs)" if recall is None else str(recall)
    gold_notes = gold.get("notes", "").strip()
    sb_notes = spellbook.get("notes", "").strip()
    by_class_rows = "\n".join(_format_by_class(gold.get("by_class", {})))

    lines = [
        BEGIN,
        "## Frozen M4 baselines (generated)",
        "",
        "Validated from `eval/baseline/*.json`. Regenerate this section with "
        "`scripts/render_status.py` (hand edits drift from baselines).",
        "",
        "### Gold-pool extras (`m4_gold_pool_summary.json`)",
        "",
        "| Metric | Value |",
        "| ------ | ----- |",
        f"| extras_total | {gold['extras_total']} |",
        f"| extras_real_card_pairs | {gold['extras_real_card_pairs']} |",
        f"| extras_fixture_pairs | {gold['extras_fixture_pairs']} |",
        f"| adjudicated (precision denominator) | {gold['adjudicated']} |",
        f"| valid | {gold['valid']} |",
        f"| precision | {gold['precision']} |",
        by_class_rows,
        "",
        f"Notes from baseline: {gold_notes}" if gold_notes else "",
        "",
        "### Spellbook recovery (`m4_spellbook_recovery_summary.json`)",
        "",
        "| Metric | Value |",
        "| ------ | ----- |",
        f"| selected | {counts.get('selected')} |",
        f"| eligible | {counts.get('eligible')} |",
        f"| rediscovered | {counts.get('rediscovered')} |",
        f"| compiler_unsupported | {counts.get('compiler_unsupported')} |",
        f"| recall_eligible | {recall_display} |",
        "",
        f"Notes from baseline: {sb_notes}" if sb_notes else "",
        END,
    ]
    # Drop empty note placeholders while keeping structure
    cleaned: list[str] = []
    for line in lines:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)
    return "\n".join(cleaned) + "\n"


def replace_generated_section(status_text: str, generated: str) -> str:
    if BEGIN not in status_text or END not in status_text:
        raise SystemExit(
            f"{STATUS_PATH}: missing {BEGIN} / {END} delimiters"
        )
    before, rest = status_text.split(BEGIN, 1)
    _, after = rest.split(END, 1)
    # generated already includes BEGIN/END
    return before + generated.rstrip("\n") + after


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if docs/STATUS.md generated section is out of sync",
    )
    args = parser.parse_args(argv)

    gold = _load_json(GOLD_BASELINE)
    spellbook = _load_json(SPELLBOOK_BASELINE)
    generated = render_generated_section(gold, spellbook)

    if not STATUS_PATH.exists():
        print(f"missing {STATUS_PATH}", file=sys.stderr)
        return 1

    current = STATUS_PATH.read_text(encoding="utf-8")
    updated = replace_generated_section(current, generated)

    if args.check:
        if current != updated:
            print(
                f"{STATUS_PATH} is out of sync with frozen baselines; "
                "run: uv run python scripts/render_status.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {STATUS_PATH} matches baselines")
        return 0

    if current != updated:
        STATUS_PATH.write_text(updated, encoding="utf-8")
        print(f"updated {STATUS_PATH}")
    else:
        print(f"unchanged {STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
