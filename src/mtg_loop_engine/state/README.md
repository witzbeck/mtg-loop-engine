# state

## Purpose

Minimal battlefield / mana / life model that verification and search mutate while checking recurrence.

## Role in pipeline

`InitialStateSpec` (proofs) → **THIS (`GameState`)** → `rules.Executor` → recurrence path reads via `get_path`.

```mermaid
graph TB;
  spec[InitialStateSpec] --> game[GameState];
  game --> executor[rules.Executor];
  executor --> game;
  game --> recurrence[verify.check_recurrence];
```

## Inputs

- `InitialStateSpec` / permanent specs from witnesses
- Mutations applied by the executor

## Outputs

- `GameState` copies for before/after comparison
- Path-addressable values for `LoopRelevantState` dimensions

## Responsibilities

- Represent permanents, mana pools, life, pending triggers, and event counters needed by the modeled rules surface.
- Provide `from_spec`, `copy`, and `get_path` for recurrence.
- Path `permanents.<id>.once_per_turn_used.<ability_id>` → boolean (whether that ability id is marked used this turn).

## Non-responsibilities

- UI, decks, full zone model, multiplayer politics
- Deciding whether a loop is verified

## Core invariants

- Path API must stay stable for authored `relevant_state` dimensions.
- Copies must be deep enough that before/after recurrence is meaningful.

## Main entry points

- `game.py`: `Permanent`, `GameState`

## Data contracts

Aligns with `proofs.models.InitialStateSpec` and `LoopRelevantState` path strings (`EXACT` / `MINIMUM` / `MAXIMUM` comparisons live in verify).

## Failure behavior

Missing paths raise `KeyError` during recurrence → verifier rejects (`STATE_NOT_RECURRENT`).

## Testing

`tests/unit/test_recurrence.py` and explorer/gold suites.

## Extension guide

Add state fields only when recurrence or effects need them. Prefer proof-relevant dimensions over decorative board chrome.

## Bigger-picture relationship

State is the board algebra under verify/search. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).
