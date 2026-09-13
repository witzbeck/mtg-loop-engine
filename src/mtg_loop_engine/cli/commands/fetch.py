"""Download Scryfall and Spellbook snapshots into gitignored data/."""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    @cli.command("fetch-scryfall", help="Download Oracle Cards snapshot")
    def fetch_scryfall() -> None:
        """Download Scryfall Oracle Cards bulk snapshot into gitignored ``data/``."""
        from mtg_loop_engine.cards.ingest import download_oracle_snapshot

        manifest = download_oracle_snapshot()
        click.echo(json.dumps(manifest, indent=2))
        raise SystemExit(0)

    @cli.command("fetch-spellbook", help="Download Spellbook sample")
    @click.option("--pages", type=int, default=2, help="Max Spellbook API pages to fetch")
    def fetch_spellbook(pages: int) -> None:
        """Download Commander Spellbook sample pages into gitignored ``data/``."""
        from mtg_loop_engine.benchmark.spellbook import download_spellbook_snapshot

        manifest = download_spellbook_snapshot(max_pages=pages)
        click.echo(json.dumps(manifest, indent=2))
        raise SystemExit(0)
