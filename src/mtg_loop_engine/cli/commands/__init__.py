"""Click command registration for the product CLI."""

from __future__ import annotations

import click

from mtg_loop_engine.cli.commands import compile, discover, eval, fetch, verify


def register_all(cli: click.Group) -> None:
    verify.register(cli)
    fetch.register(cli)
    compile.register(cli)
    discover.register(cli)
    eval.register(cli)
