# mtg_loop_engine

## Purpose

Core library: card ingest, semantic IR, capability joins, bounded discovery, game state, rules surface, witness verification, proofs, benchmarks, and curated gold corpora.

## Context

```mermaid
graph TB;
  cards[cards] --> semantics[semantics];
  semantics --> verify[verify];
  semantics --> interactions[interactions];
  interactions --> search[search];
  search --> verify;
  state[state] --> verify;
  rules[rules] --> verify;
  verify --> proofs[proofs];
  corpus[corpus] --> verify;
  corpus --> search;
  benchmark[benchmark] --> corpus;
```

## What belongs here

- Library modules imported as `mtg_loop_engine.*`
- Manual gold fixtures under `corpus/`

## What does not belong here

- CLI-only scripts that belong in `scripts/`
- UI / API apps
