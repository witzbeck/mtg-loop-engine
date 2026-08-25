# src

## Purpose

Installable Python source tree (`src` layout) for the `mtg_loop_engine` package.

## Role in pipeline

Repo layout → **THIS** → installed `mtg_loop_engine` library (and CLI entrypoint declared in `pyproject.toml`).

## Inputs

- Package modules authored under `mtg_loop_engine/`.

## Outputs

- An importable distribution consumed by tests, CLI, and scripts.

## Responsibilities

- Hold the only installable library code for the engine.
- Preserve `src` layout so editable installs and packaging stay predictable.

## Boundaries

| Concern | Owner |
| --- | --- |
| Tests | `tests/` |
| Committed eval metadata | `eval/` |
| Gitignored snapshots | `data/` |
| Operator docs | `docs/` |

## Core invariants

- Engine logic lives under `mtg_loop_engine/`.
- Oracle bulk JSON stays under gitignored `data/`.

## Main entry points

- Package root: `mtg_loop_engine/`
- Console script: `mtg-loop-engine` → `mtg_loop_engine.cli:main`

## Data contracts

N/A (layout container).

## Failure behavior

N/A.

## Testing

Exercised indirectly by the full pytest suite importing the installed package.

## Extension guide

Add new library modules under `mtg_loop_engine/<package>/` with a local `README.md` operating contract. Ad-hoc scripts belong in `scripts/` or as CLI subcommands.

## Bigger-picture relationship

See [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). Package boundaries and dependency direction live there; this folder only defines where installable code lives.
