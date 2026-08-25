#!/usr/bin/env python3
"""Blind-discover among COMPLETE Spellbook cards; label ABSENT_FROM_REFERENCE."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mtg_loop_engine.benchmark.spellbook import is_conventional_two_card
from mtg_loop_engine.eval.reference_absent import classify_discovery_vs_reference
from mtg_loop_engine.eval.spellbook_eval import load_variant_jsonl, variant_card_names
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from spellbook_compiler_priority import build_name_index, lookup_semantics  # noqa: E402

DEFAULT_VARIANTS = REPO_ROOT / "data" / "spellbook" / "latest" / "variants_two_card.jsonl"
DEFAULT_SCRYFALL = REPO_ROOT / "data" / "scryfall" / "latest"
DEFAULT_OUT = REPO_ROOT / "data" / "eval" / "absent_discovery_report.json"


def complete_cards_from_variants(
    variants: list[dict[str, Any]],
    scryfall_dir: Path,
) -> tuple[list[CardSemantics], set[frozenset[str]], dict[str, Any]]:
    names: set[str] = set()
    reference: set[frozenset[str]] = set()
    for variant in variants:
        card_names = variant_card_names(variant)
        names.update(card_names)
        if len(card_names) == 2:
            reference.add(frozenset(n.casefold() for n in card_names))
    index, unresolved = build_name_index(scryfall_dir, names)
    cards: list[CardSemantics] = []
    for name in sorted(names):
        sem = lookup_semantics(name, index)
        if sem is not None and sem.coverage == SemanticCoverage.COMPLETE:
            cards.append(sem)
    meta = {
        "unique_names": len(names),
        "unresolved_names": len(unresolved),
        "complete_cards": len(cards),
        "reference_pairs": len(reference),
    }
    return cards, reference, meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", type=Path, default=DEFAULT_VARIANTS)
    parser.add_argument("--scryfall-dir", type=Path, default=DEFAULT_SCRYFALL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-depth", type=int, default=6)
    args = parser.parse_args()

    if not args.variants.exists():
        raise SystemExit(f"missing variants: {args.variants}")
    if not args.scryfall_dir.exists():
        raise SystemExit(f"missing scryfall snapshot: {args.scryfall_dir}")

    variants = [
        v for v in load_variant_jsonl(args.variants) if is_conventional_two_card(v)
    ]
    cards, reference, meta = complete_cards_from_variants(variants, args.scryfall_dir)
    discovery = discover_loops(cards, max_depth=args.max_depth)
    report = classify_discovery_vs_reference(discovery, reference)
    payload = {
        "inputs": {
            "variants_path": str(args.variants),
            "variant_count": len(variants),
            **meta,
        },
        "report": report.model_dump(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "complete_cards": meta["complete_cards"],
                "verified": report.verified,
                "in_reference": report.in_reference,
                "absent_from_reference": report.absent_from_reference,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
