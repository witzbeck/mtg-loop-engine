"""Click CLI wiring: help, version, and gate exit codes."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from mtg_loop_engine import __version__
from mtg_loop_engine.cli import cli

COMMANDS = [
    "verify-gold",
    "verify-physics",
    "fetch-scryfall",
    "fetch-spellbook",
    "compile-coverage",
    "discover-gold",
    "discover-physics",
    "eval-gold-extras",
    "eval-spellbook",
    "adjudicate-workbench",
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_root_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "verify-gold" in result.output


@pytest.mark.parametrize("command", COMMANDS)
def test_command_help(runner: CliRunner, command: str) -> None:
    result = runner.invoke(cli, [command, "--help"])
    assert result.exit_code == 0
    assert command in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_eval_spellbook_missing_variants_exits_one(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["eval-spellbook", "--variants", "/nonexistent/variants.jsonl"],
    )
    assert result.exit_code == 1
    assert "missing variants jsonl" in result.stderr


def test_no_command_shows_usage(runner: CliRunner) -> None:
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert "Usage:" in result.output
