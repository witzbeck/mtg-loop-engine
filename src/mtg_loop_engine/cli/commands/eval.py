"""M4 evaluation commands and adjudication workbench launcher."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mtg_loop_engine.cli._subprocess import run_managed_subprocess


def register(cli: click.Group) -> None:
    @cli.command(
        "eval-gold-extras",
        help="Snapshot and adjudicate extra gold-pool discoveries",
    )
    def eval_gold_extras() -> None:
        """Snapshot gold-pool extra discoveries and report adjudicated precision."""
        from mtg_loop_engine.eval.gold_extras import persist_gold_pool_extras
        from mtg_loop_engine.eval.metrics import precision_from_records
        from mtg_loop_engine.eval.store import DEFAULT_JSONL, AdjudicationStore
        from mtg_loop_engine.semantics.provenance import is_precision_eligible_ids

        store = AdjudicationStore()
        extras = persist_gold_pool_extras(store)
        adjs = {
            record.candidate_id: store.get_adjudication(record.candidate_id)
            for record in extras
        }
        precision_extras = [
            r for r in extras if is_precision_eligible_ids(r.left_id, r.right_id)
        ]
        report = precision_from_records(
            precision_extras, {k: v for k, v in adjs.items() if v}
        )
        click.echo(
            json.dumps(
                {
                    "extras_total": len(extras),
                    "extras_real_card_pairs": len(precision_extras),
                    "extras_fixture_pairs": len(extras) - len(precision_extras),
                    "adjudicated": report.adjudicated,
                    "valid": report.valid,
                    "precision": report.precision,
                    "by_class": report.by_class,
                    "jsonl": str(DEFAULT_JSONL),
                },
                indent=2,
            )
        )
        store.close()
        raise SystemExit(0)

    @cli.command(
        "eval-spellbook",
        help="Reference recovery on a conventional two-card JSONL",
    )
    @click.option(
        "--variants",
        type=click.Path(path_type=Path),
        default=Path("eval/fixtures/spellbook_conventional_sample.jsonl"),
        show_default=True,
        help="JSONL of Spellbook-shaped variants (pair labels used only for scoring)",
    )
    @click.option(
        "--fetch-oracle",
        is_flag=True,
        help="Resolve missing names via Scryfall collection API, then compile deterministically",
    )
    @click.option(
        "--out",
        type=click.Path(path_type=Path),
        default=None,
        help="Write RecoveryReport JSON to this path",
    )
    def eval_spellbook(
        variants: Path,
        fetch_oracle: bool,
        out: Path | None,
    ) -> None:
        """Reference recovery on a conventional two-card Spellbook-shaped JSONL."""
        from mtg_loop_engine.eval.spellbook_eval import (
            evaluate_reference_subset,
            fixtures_by_name,
            load_variant_jsonl,
        )

        if not variants.exists():
            click.echo(f"missing variants jsonl: {variants}", err=True)
            click.echo(
                "Provide a conventional two-card JSONL (see eval/fixtures/) "
                "or fetch-spellbook and point at data/spellbook/latest/variants_two_card.jsonl",
                err=True,
            )
            raise SystemExit(1)
        loaded = load_variant_jsonl(variants)
        cards = fixtures_by_name()
        if fetch_oracle:
            from mtg_loop_engine.eval.oracle_lookup import (
                fetch_named_semantics,
                names_from_variants,
            )

            fetched = fetch_named_semantics(names_from_variants(loaded))
            cards = {**cards, **fetched}
        report = evaluate_reference_subset(loaded, cards_by_name=cards)
        click.echo(report.model_dump_json(indent=2))
        if out is not None:
            out.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        raise SystemExit(0)

    @cli.command(
        "adjudicate-workbench",
        help="Launch the local Streamlit M4 adjudication workbench",
    )
    def adjudicate_workbench() -> None:
        """Launch local Streamlit adjudication UI (requires eval optional deps)."""
        from mtg_loop_engine.eval.store import (
            DEFAULT_DB,
            DuckDBLockError,
            assert_db_unlocked,
        )

        try:
            assert_db_unlocked(DEFAULT_DB)
        except DuckDBLockError as exc:
            click.echo(str(exc), err=True)
            raise SystemExit(1) from exc

        app = Path(__file__).resolve().parents[2] / "eval" / "workbench.py"
        raise SystemExit(
            run_managed_subprocess(
                [sys.executable, "-m", "streamlit", "run", str(app)]
            )
        )
