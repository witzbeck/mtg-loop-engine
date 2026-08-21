# mtg_loop_engine

## Purpose

Core library for explainable two-card loop discovery: Oracle ingest, deterministic semantics, capability joins, bounded search, rules-aware verification, curated corpora, and M4 evaluation instrumentation.

## Role in pipeline

Operators / CLI / tests → **THIS package** → `LoopWitness` / `LoopProof` / eval artifacts.

```mermaid
graph TB;
  cards[cards] --> semantics[semantics];
  semantics --> interactions[interactions];
  semantics --> rules[rules];
  semantics --> state[state];
  semantics --> proofs[proofs];
  interactions --> search[search];
  corpus[corpus] --> search;
  corpus --> verify[verify];
  rules --> verify;
  state --> verify;
  proofs --> verify;
  search --> verify;
  search -.->|classify stamp| evalPkg[eval];
  evalPkg --> search;
  benchmark[benchmark] --> evalPkg;
```

## Inputs

- Scryfall Oracle snapshots (`cards`)
- Authored gold IR / witnesses (`corpus`)
- Spellbook reference extracts (`benchmark`, gitignored under `data/`)
- Operator commands via `cli.py`

## Outputs

- Compiled `CardSemantics`, discovered `LoopWitness`, verified `LoopProof`
- Eval records, recovery/precision reports, Streamlit workbench

## Responsibilities

- Own the M0–M4 engine surface as importable modules.
- Keep discovery speculative and verification conservative.
- Expose CLI orchestration without embedding business logic in `cli.py` beyond wiring.

## Non-responsibilities

- FastAPI / Postgres / public explorer (M7)
- LLM-authored semantics on any path to `VERIFIED`
- Committed Oracle bulk JSON

## Core invariants

- **`search → verify` allowed; `verify → search` forbidden.**
- Fail-closed: `PARTIAL_RELEVANT_TO_PROOF` never yields `VERIFIED`.
- Pair labels must not enter the discovery path.
- Open defect: participant / `strict_two_card` is **detected** (classify) but **not enforced** in search acceptance. See `search/README.md` and [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).

## Main entry points

| Module | Role |
| --- | --- |
| `__init__.py` | Package version |
| `cli.py` | Operator commands (`verify-gold`, `discover-gold`, `eval-*`, `fetch-*`, …) |
| `config.py` | `EngineConfig` knobs |

Subpackages: `cards`, `semantics`, `interactions`, `search`, `verify`, `rules`, `state`, `proofs`, `corpus`, `benchmark`, `eval`.

## Data contracts

Shared schemas live in `proofs.models` (`LoopWitness`, `LoopProof`, `Classification`, …). Semantic coverage enum in `semantics.enums.SemanticCoverage`.

## Failure behavior

CLI exits non-zero on gold verification mismatches, missing Spellbook paths, or eval persistence errors. Library APIs return typed rejection proofs rather than raising for ordinary loop failures.

## Testing

Full suite under `tests/` — gold positives, hard negatives, compiled seam, discovery recall, eval instruments, and `test_search_boundary` (verify ↛ search).

## Extension guide

1. Add deterministic patterns before expanding search heuristics.
2. Keep new acceptance gates in `verify` or as explicit search pre-filters — never hide truth decisions inside joins alone.
3. Update the package README here and the touched subpackage README in the same change.

## Bigger-picture relationship

North star: Oracle → semantics → blind discovery → rules proof. Detail: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md), [`ROADMAP.md`](../../ROADMAP.md).
