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

## Non-responsibilities

- Tests (`tests/`), committed eval metadata (`eval/`), gitignored snapshots (`data/`), or operator docs (`docs/`).

## Core invariants

- No engine logic outside `mtg_loop_engine/`.
- No Oracle bulk JSON committed under this tree.

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

Add new library modules under `mtg_loop_engine/<package>/` with a local `README.md` operating contract. Do not place ad-hoc scripts here (use `scripts/` or CLI subcommands).

## Bigger-picture relationship

See [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). Package boundaries and dependency direction live there; this folder only defines where installable code lives.
