# unit

## Purpose

Focused unit tests for helpers, joins, explorer mechanics, ingest, recurrence, and **layer boundaries**.

## Role in pipeline

Individual modules → **THIS** → fast regression signals.

## Inputs

- Library units (`interactions`, `search`, `verify`, `cards`, `state`, …)

## Outputs

- Narrow asserts (including spies for verifier injection)

## Responsibilities

- Lock capability joins and inverted-index behavior.
- Prove explorer treats injected verifier as acceptance oracle and does not double-verify.
- Enforce `verify` does not import `search` (`test_search_boundary.py`).
- Cover ingest hashing, recurrence/`get_path` matrices, fingerprint search-equivalence, executor soundness, and gross-vs-net output characterization.

## Non-responsibilities

- Full gold recall (see `../discovery/`)
- Adjudication precision (see `../eval/`)

## Core invariants

- Boundary test is load-bearing architecture.
- Reject-all verifier ⇒ no discovery hits.

## Main entry points

- `test_interactions.py`, `test_explorer.py`, `test_search_boundary.py`, `test_scryfall_ingest.py`, `test_recurrence.py`, `test_executor_soundness.py`, `test_once_per_turn_recurrence.py`, `test_output_gross_vs_net.py`, `test_spellbook_filter.py`, …

## Data contracts

Match module APIs; spies must not weaken production contracts.

## Failure behavior

Unit failures block CI like any other contract.

## Testing

This suite.

## Extension guide

Prefer unit tests for local mechanics; put cross-package seams in `semantic/` or `discovery/`.

## Bigger-picture relationship

Parent: [`../README.md`](../README.md).
