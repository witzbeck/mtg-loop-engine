# eval

## Purpose

Tests for evaluation instrumentation: prerequisite **detection**, store roundtrips, Spellbook sample recovery, gold-extra adjudication coverage, fixture precision exclusions, narrate helpers.

## Role in pipeline

`mtg_loop_engine.eval` + repo-root `eval/` artifacts → **THIS** → assert measurement contracts.

## Inputs

- Discoveries, fixtures, adjudications, classify helpers

## Outputs

- Asserts on recovery stages, precision denominators, and classify flags

## Responsibilities

- Document that bystander pairs can explore successfully while `strict_two_card is False` (`test_basalt_altar_is_not_strict_two_card`) — **detection without enforcement**.
- Keep sample recovery (2/2) and extras↔adjudications (24) locked.
- Ensure fixture pairs do not inflate precision.

## Non-responsibilities

- Implementing participant enforcement (engine change tracked in ROADMAP)
- Freezing baseline JSON (manual/eval persist; checked via status scripts)

## Core invariants

- Spellbook absence is not treated as a false positive in metrics semantics.
- Precision excludes `INVALID_CANDIDATE_DATA` / fixtures.

## Main entry points

- `test_classify_store.py`, `test_spellbook_eval.py`, `test_fixture_detection.py`, `test_narrate.py`, …

## Data contracts

Aligned with `eval/baseline` notes and `eval.schema`.

## Failure behavior

Measurement regressions fail CI.

## Testing

This suite.

## Extension guide

When participant enforcement ships, invert the bystander test into an acceptance rejection regression.

## Bigger-picture relationship

Parent: [`../README.md`](../README.md). Package: [`../../src/mtg_loop_engine/eval/README.md`](../../src/mtg_loop_engine/eval/README.md).
