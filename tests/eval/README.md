# eval

## Purpose

Tests for evaluation instrumentation: prerequisite **detection**, search participant-gate regressions, store roundtrips, Spellbook sample recovery, gold-extra adjudication coverage, fixture precision exclusions, narrate helpers.

## Role in pipeline

`mtg_loop_engine.eval` + repo-root `eval/` artifacts → **THIS** → assert measurement contracts.

## Inputs

- Discoveries, fixtures, adjudications, classify helpers

## Outputs

- Asserts on recovery stages, precision denominators, and classify / acceptance flags

## Responsibilities

- Regress that real bystander pairs are **not** accepted (`test_bystander_pairs_are_not_accepted`).
- Keep sample recovery (2/2) and extras↔adjudications (10 post-gate) locked.
- Ensure fixture pairs do not inflate precision.

## Non-responsibilities

- Freezing baseline JSON (manual/eval persist; checked via status scripts). Committed baselines remain the pre-gate snapshot until ROADMAP M4 item 5.

## Core invariants

- Spellbook absence is not treated as a false positive in metrics semantics.
- Precision excludes `INVALID_CANDIDATE_DATA` / fixtures.

## Main entry points

- `test_classify_store.py`, `test_spellbook_eval.py`, `test_compiler_frontier.py`, `test_fixture_detection.py`, `test_narrate.py`, …

## Data contracts

Aligned with `eval/baseline` notes and `eval.schema`. Live discovery extras count may differ from frozen baseline until re-freeze.

## Failure behavior

Measurement regressions fail CI.

## Testing

This suite.

## Extension guide

When baselines are re-frozen after compiler/eligibility work, update extras count expectations and STATUS together.

## Bigger-picture relationship

Parent: [`../README.md`](../README.md). Package: [`../../src/mtg_loop_engine/eval/README.md`](../../src/mtg_loop_engine/eval/README.md).
