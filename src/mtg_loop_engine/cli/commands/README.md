# commands

## Purpose

Per-family Click command modules registered on the root `mtg-loop-engine` group.

## What belongs here

| Module | Commands |
| --- | --- |
| `verify.py` | `verify-gold`, `verify-physics` |
| `fetch.py` | `fetch-scryfall`, `fetch-spellbook` |
| `compile.py` | `compile-coverage` |
| `discover.py` | `discover-gold`, `discover-physics` |
| `eval.py` | `eval-gold-extras`, `eval-spellbook`, `adjudicate-workbench` |

## What does not belong here

- Root group definition (`../__init__.py`)
- Subprocess lifecycle (`../_subprocess.py`)

## Notes

Each module exposes `register(cli: click.Group) -> None`. Operator contract: [`docs/CLI.md`](../../../../docs/CLI.md).
