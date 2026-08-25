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
- Track `damage_marked`, `lifelink`, and `undying` on `Permanent` for SBA / keyword physics (rules executor).
- Provide `from_spec`, `copy`, and `get_path` for recurrence.
- Own the allowed `LoopRelevantState` path grammar (`paths.py` / `is_valid_state_path`) matching `get_path`:
  `mana.*`, `events.*`, `life.*`, `permanents.<id>.zone|tapped|counters.<type>|summoning_sick|once_per_turn_used.<ability>`,
  `pending_triggers.count`, `count.<zone>.creature_tokens|creatures|artifacts`.
- Path `permanents.<id>.once_per_turn_used.<ability_id>` → boolean (whether that ability id is marked used this turn).
- Path `pending_triggers.count` → length of the pending trigger queue (ADR 0008 mandatory).
- `Permanent.effective_toughness()` → toughness + p1p1 − m1m1 (None if no printed toughness).

## Non-responsibilities

- UI, decks, full zone model, multiplayer politics
- Deciding whether a loop is verified

## Core invariants

- Path API must stay stable for authored `relevant_state` dimensions.
- Path grammar and `get_path` must agree; grammar-invalid paths fail closed at `StateDimension` construction and in the verifier.
- Copies must be deep enough that before/after recurrence is meaningful.

## Main entry points

- `game.py`: `Permanent`, `GameState`
- `paths.py`: `is_valid_state_path`, `STATE_PATH_GRAMMAR`

## Data contracts

Aligns with `proofs.models.InitialStateSpec` and `LoopRelevantState` path strings (`EXACT` / `MINIMUM` / `MAXIMUM` comparisons live in verify).

## Failure behavior

- Grammar-invalid paths: rejected by `StateDimension` validation; verifier maps any that slip through → `STATE_NOT_RECURRENT`.
- Runtime-missing paths (unknown permanent id) raise `KeyError` during recurrence → verifier rejects (`STATE_NOT_RECURRENT`).

## Testing

`tests/unit/test_recurrence.py`, `tests/unit/test_state_path_grammar.py`, and explorer/gold suites.

## Extension guide

Add state fields only when recurrence or effects need them. Prefer proof-relevant dimensions over decorative board chrome.

## Bigger-picture relationship

State is the board algebra under verify/search. Architecture: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).
