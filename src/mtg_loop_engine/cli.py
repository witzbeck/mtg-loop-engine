"""CLI entrypoints for corpus ingest and verification demos."""

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

    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main(sys.argv[1:])
