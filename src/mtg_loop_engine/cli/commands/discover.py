"""Blind loop discovery over curated card pools."""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    @cli.command(
        "discover-gold",
        help="Blind-discover Oracle gold_core pairs (no pair labels)",
    )
    def discover_gold() -> None:
        """Blind-discover Oracle gold_core pairs (no pair labels)."""
        from mtg_loop_engine.corpus import gold_core_card_pool, gold_core_pair_keys
        from mtg_loop_engine.search.discover import discover_loops

        gold = gold_core_pair_keys()
        report = discover_loops(gold_core_card_pool())
        found = report.verified_pairs
        missing = gold - found
        click.echo(
            json.dumps(
                {
                    "cards": report.cards,
                    "candidate_pairs": report.candidate_pairs,
                    "searched_pairs": report.searched_pairs,
                    "verified": len(report.verified),
                    "gold_pairs": len(gold),
                    "rediscovered": len(gold & found),
                    "missing": [
                        sorted(p)
                        for p in sorted(missing, key=lambda s: tuple(sorted(s)))
                    ],
                },
                indent=2,
            )
        )
        for hit in report.verified:
            names = " + ".join(c.name for c in hit.witness.essential_cards)
            click.echo(f"VERIFIED  {names}  reasons={hit.reasons}")
        raise SystemExit(1 if missing else 0)

    @cli.command(
        "discover-physics",
        help="Blind-discover physics fixture pairs (no pair labels)",
    )
    def discover_physics() -> None:
        """Blind-discover physics fixture pairs (synthetic/divergent OK)."""
        from mtg_loop_engine.corpus import physics_gold_card_pool, physics_gold_pair_keys
        from mtg_loop_engine.search.discover import discover_loops

        gold = physics_gold_pair_keys()
        report = discover_loops(physics_gold_card_pool())
        found = report.verified_pairs
        missing = gold - found
        click.echo(
            json.dumps(
                {
                    "cards": report.cards,
                    "candidate_pairs": report.candidate_pairs,
                    "searched_pairs": report.searched_pairs,
                    "verified": len(report.verified),
                    "physics_pairs": len(gold),
                    "rediscovered": len(gold & found),
                    "missing": [
                        sorted(p)
                        for p in sorted(missing, key=lambda s: tuple(sorted(s)))
                    ],
                },
                indent=2,
            )
        )
        for hit in report.verified:
            names = " + ".join(c.name for c in hit.witness.essential_cards)
            click.echo(f"VERIFIED  {names}  reasons={hit.reasons}")
        raise SystemExit(1 if missing else 0)
