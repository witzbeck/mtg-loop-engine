"""Compiler coverage reporting on gold Oracle fixtures."""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    @cli.command(
        "compile-coverage",
        help="Report M2 pattern coverage on gold fixtures",
    )
    def compile_coverage() -> None:
        """Report deterministic compiler coverage on gold Oracle fixtures."""
        from mtg_loop_engine.semantics.compiler import compile_oracle_text
        from mtg_loop_engine.semantics.coverage import aggregate_coverage
        from mtg_loop_engine.semantics.oracle_fixtures import (
            GOLD_ORACLE_FIXTURES,
            UNSUPPORTED_FIXTURE,
        )

        reports = []
        for fix in GOLD_ORACLE_FIXTURES.values():
            report = compile_oracle_text(
                oracle_id=fix.oracle_id,
                name=fix.name,
                oracle_text=fix.oracle_text,
                types=fix.types,
            )
            reports.append(report)
            status = "OK" if report.coverage.value == "complete" else "PARTIAL"
            click.echo(
                f"{status:8} {fix.name}: "
                f"{report.supported_count}/{report.fragment_count} fragments"
            )
        unsupported = compile_oracle_text(
            oracle_id=UNSUPPORTED_FIXTURE.oracle_id,
            name=UNSUPPORTED_FIXTURE.name,
            oracle_text=UNSUPPORTED_FIXTURE.oracle_text,
            types=UNSUPPORTED_FIXTURE.types,
        )
        click.echo(
            f"EXPECT   {UNSUPPORTED_FIXTURE.name}: "
            f"{unsupported.coverage.value} "
            f"unsupported={len(unsupported.semantics.unsupported_fragments)}"
        )
        metrics = aggregate_coverage(reports)
        click.echo(
            json.dumps(
                {
                    "gold_cards": metrics.cards,
                    "fragment_coverage": round(metrics.fragment_coverage, 4),
                    "cards_complete": metrics.cards_complete,
                },
                indent=2,
            )
        )
        raise SystemExit(0 if metrics.fragment_coverage == 1.0 else 1)
