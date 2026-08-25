"""CLI entrypoints for ingest, verification, discovery, and M4 evaluation."""

from __future__ import annotations

import argparse
import json
import sys

from mtg_loop_engine import __version__
from mtg_loop_engine.corpus import all_gold_core, gold_extended_catalog, hard_negatives
from mtg_loop_engine.verify.verifier import Verifier


def cmd_verify_gold(_: argparse.Namespace) -> int:
    v = Verifier()
    failures = 0
    for w in all_gold_core():
        proof = v.verify(w)
        ok = proof.status.value == "verified"
        print(f"{w.id}: {proof.status.value} hash={proof.proof_hash}")
        if not ok:
            failures += 1
            print(f"  reason: {proof.rejection_reason}")
    for w in hard_negatives():
        proof = v.verify(w)
        expected = w.expected_status.value if w.expected_status else None
        match = expected is None or proof.status == w.expected_status
        print(f"{w.id}: {proof.status.value} (expected {expected}) ok={match}")
        if not match:
            failures += 1
    for w in gold_extended_catalog()[:3]:
        proof = v.verify(w)
        print(f"{w.id}: {proof.status.value}")
    return 1 if failures else 0


def cmd_fetch_scryfall(_: argparse.Namespace) -> int:
    from mtg_loop_engine.cards.ingest import download_oracle_snapshot

    manifest = download_oracle_snapshot()
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_fetch_spellbook(args: argparse.Namespace) -> int:
    from mtg_loop_engine.benchmark.spellbook import download_spellbook_snapshot

    manifest = download_spellbook_snapshot(max_pages=args.pages)
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_compile_coverage(_: argparse.Namespace) -> int:
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
        print(
            f"{status:8} {fix.name}: "
            f"{report.supported_count}/{report.fragment_count} fragments"
        )
    unsupported = compile_oracle_text(
        oracle_id=UNSUPPORTED_FIXTURE.oracle_id,
        name=UNSUPPORTED_FIXTURE.name,
        oracle_text=UNSUPPORTED_FIXTURE.oracle_text,
        types=UNSUPPORTED_FIXTURE.types,
    )
    print(
        f"EXPECT   {UNSUPPORTED_FIXTURE.name}: "
        f"{unsupported.coverage.value} "
        f"unsupported={len(unsupported.semantics.unsupported_fragments)}"
    )
    metrics = aggregate_coverage(reports)
    print(
        json.dumps(
            {
                "gold_cards": metrics.cards,
                "fragment_coverage": round(metrics.fragment_coverage, 4),
                "cards_complete": metrics.cards_complete,
            },
            indent=2,
        )
    )
    return 0 if metrics.fragment_coverage == 1.0 else 1


def cmd_discover_gold(_: argparse.Namespace) -> int:
    from mtg_loop_engine.corpus import gold_core_card_pool, gold_core_pair_keys
    from mtg_loop_engine.search.discover import discover_loops

    gold = gold_core_pair_keys()
    report = discover_loops(gold_core_card_pool())
    found = report.verified_pairs
    missing = gold - found
    print(
        json.dumps(
            {
                "cards": report.cards,
                "candidate_pairs": report.candidate_pairs,
                "searched_pairs": report.searched_pairs,
                "verified": len(report.verified),
                "gold_pairs": len(gold),
                "rediscovered": len(gold & found),
                "missing": [sorted(p) for p in sorted(missing, key=lambda s: tuple(sorted(s)))],
            },
            indent=2,
        )
    )
    for hit in report.verified:
        names = " + ".join(c.name for c in hit.witness.essential_cards)
        print(f"VERIFIED  {names}  reasons={hit.reasons}")
    return 1 if missing else 0


def cmd_eval_gold_extras(_: argparse.Namespace) -> int:
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
    print(
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
    return 0


def cmd_eval_spellbook(args: argparse.Namespace) -> int:
    from pathlib import Path

    from mtg_loop_engine.eval.spellbook_eval import (
        evaluate_reference_subset,
        fixtures_by_name,
        load_variant_jsonl,
    )

    path = Path(args.variants)
    if not path.exists():
        print(f"missing variants jsonl: {path}", file=sys.stderr)
        print(
            "Provide a conventional two-card JSONL (see eval/fixtures/) "
            "or fetch-spellbook and point at data/spellbook/latest/variants_two_card.jsonl",
            file=sys.stderr,
        )
        return 1
    variants = load_variant_jsonl(path)
    cards = fixtures_by_name()
    if args.fetch_oracle:
        from mtg_loop_engine.eval.oracle_lookup import fetch_named_semantics, names_from_variants

        fetched = fetch_named_semantics(names_from_variants(variants))
        cards = {**cards, **fetched}
    report = evaluate_reference_subset(variants, cards_by_name=cards)
    print(report.model_dump_json(indent=2))
    if args.out:
        Path(args.out).write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_adjudicate_workbench(_: argparse.Namespace) -> int:
    from pathlib import Path
    import subprocess

    app = Path(__file__).resolve().parent / "eval" / "workbench.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="mtg-loop-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gold = sub.add_parser("verify-gold", help="Run gold_core + hard negatives")
    p_gold.set_defaults(func=cmd_verify_gold)

    p_sc = sub.add_parser("fetch-scryfall", help="Download Oracle Cards snapshot")
    p_sc.set_defaults(func=cmd_fetch_scryfall)

    p_sb = sub.add_parser("fetch-spellbook", help="Download Spellbook sample")
    p_sb.add_argument("--pages", type=int, default=2)
    p_sb.set_defaults(func=cmd_fetch_spellbook)

    p_cov = sub.add_parser(
        "compile-coverage", help="Report M2 pattern coverage on gold fixtures"
    )
    p_cov.set_defaults(func=cmd_compile_coverage)

    p_disc = sub.add_parser(
        "discover-gold",
        help="Blind-discover gold_core pairs (no pair labels)",
    )
    p_disc.set_defaults(func=cmd_discover_gold)

    p_ex = sub.add_parser(
        "eval-gold-extras",
        help="Snapshot and adjudicate extra gold-pool discoveries",
    )
    p_ex.set_defaults(func=cmd_eval_gold_extras)

    p_sp = sub.add_parser(
        "eval-spellbook",
        help="Reference recovery on a conventional two-card JSONL",
    )
    p_sp.add_argument(
        "--variants",
        default="eval/fixtures/spellbook_conventional_sample.jsonl",
        help="JSONL of Spellbook-shaped variants (pair labels used only for scoring)",
    )
    p_sp.add_argument(
        "--fetch-oracle",
        action="store_true",
        help="Resolve missing names via Scryfall collection API, then compile deterministically",
    )
    p_sp.add_argument("--out", help="Write RecoveryReport JSON to this path")
    p_sp.set_defaults(func=cmd_eval_spellbook)

    p_wb = sub.add_parser(
        "adjudicate-workbench",
        help="Launch the local Streamlit M4 adjudication workbench",
    )
    p_wb.set_defaults(func=cmd_adjudicate_workbench)

    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main(sys.argv[1:])
