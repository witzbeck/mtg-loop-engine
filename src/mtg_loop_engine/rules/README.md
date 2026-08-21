# rules

## Purpose

Modeled Comprehensive Rules subset: execute costs, effects, simple triggers, cost modifiers, and replacements against `GameState`.

## Role in pipeline

`CardSemantics` + `ActionStep` sequences → **THIS (`Executor`)** → mutated `GameState` or typed `ExecError` → consumed by `verify` and `search`.

```mermaid
graph TB;
  semantics[CardSemantics] --> executor[Executor];
  state[GameState] --> executor;
  steps[ActionSteps] --> executor;
  executor -->|ok| nextState[GameState];
  executor -->|fail| execError[ExecError];
```

## Inputs

- Semantics map (`oracle_id → CardSemantics`)
- `GameState` and `ActionStep` / sequences from proofs models

## Outputs

- Updated `GameState` on success
- `ExecError` with status/message on illegal or resource-failing steps

## Responsibilities

- Replay setup and loop actions faithfully within the modeled rules surface.
- Combo-player favorable / opponent adversarial choice ownership (see executor docstring and frozen product decisions).

## Non-responsibilities

- Pair discovery or BFS (`search/`)
- Full CR implementation
- Accepting or rejecting loops as proofs (`verify/` owns that)

## Core invariants

- Execution errors become typed verification failures upstream — no silent illegal success.
- Cost reduction and trigger resolution must match what patterns claim to support.

## Main entry points

- `executor.py`: `Executor`, `ExecError`, `run_step` / `run_sequence`

## Data contracts

Action ops and effect shapes from `semantics` / `proofs.models`. Statuses align with `VerificationStatus` vocabulary where applicable (`RESOURCE_DEFICIT`, `ILLEGAL_ACTION`, …).

## Failure behavior

Return `ExecError` rather than mutating into an illegal board. Verifier maps these into rejection proofs.

## Testing

Indirect via gold_core, hard_negatives, explorer unit tests, and compile→verify seam tests.

## Extension guide

To add a **rule primitive** (new modeled cost, effect, trigger, or replacement the engine can execute): extend `executor.py` only when a new semantic pattern requires that physics. Keep search free of rules special-cases that belong here. Pair every new capability with a hard-negative or gold regression when it changes acceptance.

## Bigger-picture relationship

Rules are the physics under the acceptance boundary. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).
