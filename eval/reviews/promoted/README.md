# promoted

## Purpose

**Exceptional only:** compact, reviewed evidence packages when a Loop Adjudication Review (LAR) does something historically important — milestone exit, ADR motivation, systemic defect, methodology establishment.

## What belongs here

Each `<evidence_id>/` directory should contain the **minimum sufficient durable evidence**, typically:

- `summary.md` — human-authored, tempered claims
- `manifest.json` — semantic provenance (schema v2)
- `comparison.json` — structured cross-tier signals

## What does not belong here

- Routine LAR runs (use gitignored `data/eval/lar/runs/<run_id>/`)
- Raw subagent transcripts
- Full phase-a/b/c JSON trees unless indispensable to the promoted claim

## Promotion criteria

Promote when the run:

- supports a milestone exit or materially changes product confidence;
- motivates an ADR or architecture correction;
- validates closure of a serious defect;
- establishes a materially new evaluation methodology.

Otherwise route findings to `eval/adjudications/`, `eval/calibration/`, `tests/`, `docs/`, or `eval/baseline/` via normal PR review.

## Related

- Process: [`../README.md`](../README.md)
- Runbook: [`docs/runbooks/LOOP_ADJUDICATION_REVIEW.md`](../../docs/runbooks/LOOP_ADJUDICATION_REVIEW.md)
