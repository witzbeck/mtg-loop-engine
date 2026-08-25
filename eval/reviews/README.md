# reviews

## Purpose

LAR **process contract** and **exceptional promoted evidence**.

Normal Loop Adjudication Review (LAR) execution is **ephemeral** under gitignored `data/eval/lar/runs/`. Findings that earn durable epistemic status land in `promoted/` or sibling `eval/` trees through human-reviewed promotion.

## Two planes

```mermaid
graph TB;
  exec[data/eval/lar/runs ephemeral]
    --> review[Human promotion review];
  review --> promoted[promoted/ exceptional];
  review --> adj[../adjudications/];
  review --> cal[../calibration/];
  review --> tests[tests/];
  review --> docs[docs/];
  promoted --> input[Future LAR input];
  adj --> input;
  cal --> input;
```

## What belongs here

| Path | Role |
|------|------|
| `_template/` | Version-controlled run contract (manifest v2 example, schemas) |
| `promoted/<evidence_id>/` | Compact exceptional evidence packages only |
| This README | Lifecycle + promotion contract |

## Boundaries

| Concern | Owner |
| --- | --- |
| Routine / timestamped run trees | Deprecated under this folder; use `data/eval/lar/runs/` |
| Raw subagent transcripts from ordinary runs | `data/eval/lar/runs/<run_id>/raw/` |
| Frozen baselines | `../baseline/` |
| Observed adjudications | `../adjudications/` |

## Normal run location

```text
data/eval/lar/runs/<run_id>/
  manifest.json
  phase-a/
  phase-b/
  phase-c/
  challenge/
  comparison.json
  synthesis.md
  promotion_candidates.json
  raw/
```

Safe to delete locally; recreated by evaluation. Ephemeral — not a STATUS authority.

## Exceptional promotion

Promote to `promoted/<evidence_id>/` only when a run:

- supports a milestone exit or materially changes product confidence;
- motivates an ADR;
- reveals systemic architecture defects or validates serious defect closure;
- establishes a materially new evaluation methodology.

Minimum package: `summary.md`, `manifest.json`, `comparison.json`.

See [`promoted/README.md`](promoted/README.md) and [`promoted/0001-m4-lar-v1/`](promoted/0001-m4-lar-v1/) for the first promoted package (M4 LAR v1).

## Process

Runbook: [`docs/runbooks/LOOP_ADJUDICATION_REVIEW.md`](../../docs/runbooks/LOOP_ADJUDICATION_REVIEW.md)

## Promotion discipline

LAR agents may emit `promotion_candidates[]` but **must not** mutate committed adjudications, calibration cases, engine code, or baselines during the review. Promotion is a follow-up PR governed by humans.

## Schemas

Authoritative models: `mtg_loop_engine.eval.lar_contracts`. Examples in `_template/`.

## Notes

- Use `suspected_layer` / `diagnostic_layer` in synthesis — disagreement alone does not assign architecture ownership.
- Report **information gain**; keep LAR signals separate (see [`docs/EVALUATION.md`](../../docs/EVALUATION.md)).
- Parallel same-model reviewers are throughput, not statistical independence.
