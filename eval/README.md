# eval

## Purpose

Committed M4 evaluation metadata: Spellbook-shaped fixtures, gold-pool extra adjudications, and frozen baseline summaries.

Working DuckDB files stay gitignored under `data/eval/`. Library code lives in `src/mtg_loop_engine/eval/`.

## Role in pipeline

Package `mtg_loop_engine.eval` writers/readers → **THIS (artifacts)** → CI tests, `docs/STATUS.md`, human review.

```mermaid
graph TB;
  pkgEval[mtg_loop_engine.eval] --> fixtures[fixtures];
  pkgEval --> adjudications[adjudications];
  pkgEval --> baseline[baseline];
  fixtures --> tests[tests/eval];
  adjudications --> precision[adjudicatedPrecision];
  baseline --> status[docs/STATUS.md];
```

## Inputs

- Outputs of `eval-gold-extras`, `eval-spellbook`, and adjudication workbench persistence

## Outputs

| Path | Role |
| --- | --- |
| `fixtures/` | Tiny conventional Spellbook JSONL for CI |
| `adjudications/` | Persisted extras + human labels |
| `baseline/` | Frozen M4 metric snapshots |

## Responsibilities

- Keep committed evaluation artifacts reviewable and CI-stable.
- Separate **reference recovery** baselines from **human-adjudicated precision** baselines.

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
