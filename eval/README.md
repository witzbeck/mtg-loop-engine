# eval

## Purpose

Committed M4 **evaluation knowledge**: fixtures, observed adjudications, taxonomy calibration, frozen baselines, and exceptional promoted review evidence — not ordinary LAR execution output.

Working DuckDB files stay gitignored under `data/eval/`. Library code lives in `src/mtg_loop_engine/eval/`.

## Role in pipeline

Package `mtg_loop_engine.eval` writers/readers → **THIS (artifacts)** → CI tests, `docs/STATUS.md`, human review.

```mermaid
graph TB;
  pkgEval[mtg_loop_engine.eval] --> fixtures[fixtures];
  pkgEval --> adjudications[adjudications];
  pkgEval --> calibration[calibration];
  pkgEval --> baseline[baseline];
  fixtures --> tests[tests/eval];
  adjudications --> precision[adjudicatedPrecision];
  calibration --> lar[LAR calibration tier];
  baseline --> status[docs/STATUS.md];
```

## Inputs

- Outputs of `eval-gold-extras`, `eval-spellbook`, and adjudication workbench persistence

## Outputs

| Path | Role |
| --- | --- |
| `fixtures/` | Tiny conventional Spellbook JSONL for CI |
| `adjudications/` | Observed extras + human labels (what engine produced) |
| `calibration/` | Curated taxonomy boundary cases (what classes mean) |
| `baseline/` | Certified M4 metric snapshots |
| `reviews/promoted/` | Exceptional LAR evidence packages only |

## Responsibilities

- Keep committed evaluation artifacts reviewable and CI-stable.
- Separate **reference recovery** baselines from **human-adjudicated precision** baselines.
- Separate **observed adjudications** from **calibration** cases.
- Keep ephemeral LAR runs under gitignored `data/eval/lar/runs/` — not here.

### Measurement split (do not conflate)

| Instrument | Question | Spellbook absence |
| --- | --- | --- |
| Reference recovery | Eligible/supported rediscovery | N/A (eligible denominator) |
| Adjudicated precision | Valid among real-card accepted discoveries | `ABSENT_FROM_REFERENCE` ≠ false positive |

Prefer numbers in `baseline/*.json` over narrative elsewhere.

## Non-responsibilities

- Scryfall Oracle bulk JSON
- Full Spellbook snapshots (`data/spellbook/`)
- Engine implementation
- M7 explorer

## Core invariants

- Fixture pairs are not precision positives (`INVALID_CANDIDATE_DATA`).
- Baselines are distribution records, not join-tuning targets.
- CI must pass using fixtures without network downloads.

## Main entry points

- Consumed by `tests/eval/`, `scripts/render_status.py`, and docs status checks
- Produced via CLI eval commands (see [`docs/CLI.md`](../docs/CLI.md))

## Data contracts

JSON/JSONL schemas aligned with `mtg_loop_engine.eval.schema` and metrics summary shapes.

## Failure behavior

Tests fail if sample recovery or extras↔adjudication coverage regresses. STATUS check fails if prose drifts from baselines.

## Testing

`tests/eval/test_spellbook_eval.py`, fixture-detection tests, gold-extra coverage.

## Extension guide

Regenerate baselines deliberately (see `baseline/README.md`). Update adjudications when re-reviewing extras; do not silently rewrite classes to improve precision.

## Bigger-picture relationship

Artifact half of M4. Code half: [`../src/mtg_loop_engine/eval/README.md`](../src/mtg_loop_engine/eval/README.md). Architecture: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
