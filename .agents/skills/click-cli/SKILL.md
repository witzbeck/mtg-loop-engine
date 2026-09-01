---
name: click-cli
description: >-
  Add or change mtg-loop-engine Click commands. Use when editing
  src/mtg_loop_engine/cli/, adding flags, exit codes, CLI wiring tests,
  or syncing docs/CLI.md and operator docs.
---

# Click CLI development

**Authority:** [`docs/CLI.md`](../../../docs/CLI.md) is the operator contract. [`AGENTS.md`](../../../AGENTS.md) epistemic boundaries are unchanged.

## Thin wiring

- Commands import library functions; no verifier, search, or compiler logic in `cli/`.
- Extract fat logic to packages before adding flags.

## File placement

| Concern | Location |
| --- | --- |
| Root group + version | `src/mtg_loop_engine/cli/__init__.py` |
| Command family | `src/mtg_loop_engine/cli/commands/<family>.py` |
| Subprocess lifecycle | `src/mtg_loop_engine/cli/_subprocess.py` |
| Registration | `register(cli: click.Group)` in each commands module; called from `commands/__init__.py` |

## Checklist for new or changed commands

1. `@cli.command("kebab-name", help="one-liner")` on the **root** group (flat unless human widens scope).
2. Docstring = long `--help` body.
3. Paths: `click.Path(path_type=Path)`; counts: `type=int`; booleans: `is_flag=True`.
4. Exit codes: `raise SystemExit(code)`; stderr via `click.echo(..., err=True)`.
5. Update [`docs/CLI.md`](../../../docs/CLI.md): command table, flags, exit codes.
6. Add `CliRunner` test in [`tests/unit/test_cli_wiring.py`](../../../tests/unit/test_cli_wiring.py): `--help` plus any gate exit code.
7. Sync root [`README.md`](../../../README.md) smoke block and owning package README when domain-specific.

## Doc sync (same PR)

- [`docs/CLI.md`](../../../docs/CLI.md)
- Root [`README.md`](../../../README.md) command examples
- Package README under `src/mtg_loop_engine/<domain>/` if the command is domain-owned

## Anti-patterns

- Rich, Typer, or nested groups without flat aliases
- Domain logic in CLI modules
- Hitchhiking Streamlit's transitive Click (product CLI pins Click in `[project.dependencies]`)
- Promoting `scripts/check_docs.py` into the product CLI
- Un-omitting `cli/` from the coverage gate to manufacture %

## Testing snippet

```python
from click.testing import CliRunner
from mtg_loop_engine.cli import cli

def test_my_command_help():
    result = CliRunner().invoke(cli, ["my-command", "--help"])
    assert result.exit_code == 0
    assert "my-command" in result.output
```

Invoke the **root group** `cli`, not the leaf function, when testing dispatch and group-level options.

## Shell completion

Document in `docs/CLI.md` when adding commands operators will complete frequently. Completion requires an installed entry point (`_MTG_LOOP_ENGINE_COMPLETE={bash,zsh,fish}_source`).
