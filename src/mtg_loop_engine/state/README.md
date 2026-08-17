# state

## Purpose

Executable game state for witness replay: permanents, mana, life, event counters, and path resolution used by `LoopRelevantState`.

## Context

```mermaid
graph TB;
  initial[InitialStateSpec] --> game[GameState];
  game --> verify[verify];
  proofs[proofs models] --> game;
```

## What belongs here

- `game.py`: `Permanent`, `GameState`, `get_path` for recurrence dimensions

## What does not belong here

- Full multiplayer UI state or decklists
- Search / candidate generation
