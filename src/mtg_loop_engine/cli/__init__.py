"""CLI entrypoints for ingest, verification, discovery, and M4 evaluation."""

from __future__ import annotations

import click

from mtg_loop_engine import __version__
from mtg_loop_engine.cli._subprocess import run_managed_subprocess
from mtg_loop_engine.cli.commands import register_all

__all__ = ["cli", "main", "run_managed_subprocess"]


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="mtg-loop-engine")
def cli() -> None:
    """Explainable two-card MTG loop discovery: compile, verify, and prove."""


register_all(cli)


def main() -> None:
    """Console script entry point."""
    cli()


if __name__ == "__main__":
    main()
