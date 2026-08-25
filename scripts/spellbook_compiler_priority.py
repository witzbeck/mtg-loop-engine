#!/usr/bin/env python3
"""Rank Spellbook compiler gaps from a variant JSONL + local Scryfall snapshot."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from mtg_loop_engine.benchmark.spellbook import is_conventional_two_card
from mtg_loop_engine.cards.ingest import load_oracle_cards, read_manifest
from mtg_loop_engine.eval.metrics import RecoveryReport
from mtg_loop_engine.eval.oracle_lookup import oracle_text_from_card, types_from_line
from mtg_loop_engine.eval.spellbook_eval import (
    compile_card,
    evaluate_reference_subset,
    load_variant_jsonl,
    variant_card_names,
)
from mtg_loop_engine.semantics.ir import CardSemantics

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VARIANTS = REPO_ROOT / "data" / "spellbook" / "latest" / "variants_two_card.jsonl"
DEFAULT_SCRYFALL = REPO_ROOT / "data" / "scryfall" / "latest"
DEFAULT_OUT_JSON = REPO_ROOT / "data" / "eval" / "compiler_priority_report.json"
DEFAULT_OUT_MD = REPO_ROOT / "data" / "eval" / "compiler_priority_report.md"
DEFAULT_RECOVERY = REPO_ROOT / "data" / "eval" / "live_spellbook_recovery_50p.json"

MECHANIC_NEEDLES: dict[str, tuple[str, ...]] = {
    "zone_recursion_sacrifice": (
        "sacrifice",
        "graveyard",
        "return",
        "altar",
        "crawler",
        "skeleton",
    ),
    "mana_tap_untap": ("untap", "tap", "mana", "monolith", "basalt"),
    "copy_imprint": ("copy", "imprint", "isochron", "scepter", "dramatic reversal"),
    "life_drain": ("life", "blood", "vito", "sanguine", "exquisite"),
    "token_etb": ("token", "enters the battlefield", "etb", "intruder alarm"),
    "counters_damage": ("counter", "damage", "ping", "-X/-X"),
    "cost_reduction": ("cost", "less to activate", "training grounds"),
}


def _normalize_fragment(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed[:120]


def _lookup_keys(name: str) -> list[str]:
    keys = [name.casefold()]
    if "//" in name:
        front = name.split("//")[0].strip()
        keys.append(front.casefold())
    return keys


def build_name_index(
    scryfall_dir: Path,
    needed_names: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Stream local Oracle bulk; index only names required by the variant set."""
    needed = {n.casefold() for n in needed_names}
    index: dict[str, dict[str, Any]] = {}
    missing_after_scan: list[str] = []
    for card in load_oracle_cards(scryfall_dir):
        name = str(card.get("name") or "")
        key = name.casefold()
        if key in needed and key not in index:
            index[key] = card
    for name in sorted(needed_names):
        if not any(k in index for k in _lookup_keys(name)):
            missing_after_scan.append(name)
    return index, missing_after_scan


def semantics_from_scryfall(card: dict[str, Any]) -> CardSemantics:
    name = str(card.get("name") or "")
    oracle_id = str(card.get("oracle_id") or card.get("id") or name)
    text = oracle_text_from_card(card)
    types = types_from_line(card.get("type_line"))
    return compile_card(oracle_id, name, text, types)


def lookup_semantics(name: str, index: dict[str, dict[str, Any]]) -> CardSemantics | None:
    for key in _lookup_keys(name):
        card = index.get(key)
        if card is not None:
            return semantics_from_scryfall(card)
    return None


def tag_mechanic(*texts: str) -> list[str]:
    blob = " ".join(texts).lower()
    hits = [family for family, needles in MECHANIC_NEEDLES.items() if any(n in blob for n in needles)]
    return hits or ["other"]


def run_analysis(
    variants_path: Path,
    scryfall_dir: Path,
    *,
    write_recovery: Path | None = None,
) -> dict[str, Any]:
    variants = load_variant_jsonl(variants_path)
    selected = [v for v in variants if is_conventional_two_card(v)]
    all_names: set[str] = set()
    for variant in selected:
        all_names.update(variant_card_names(variant))

    scryfall_manifest = read_manifest(scryfall_dir)
    name_index, unresolved_names = build_name_index(scryfall_dir, all_names)

    cards_by_name: dict[str, CardSemantics] = {}
    for name in all_names:
        sem = lookup_semantics(name, name_index)
        if sem is not None:
            cards_by_name[name.casefold()] = sem

    recovery = evaluate_reference_subset(selected, cards_by_name=cards_by_name)
    if write_recovery is not None:
        write_recovery.parent.mkdir(parents=True, exist_ok=True)
        write_recovery.write_text(recovery.model_dump_json(indent=2) + "\n", encoding="utf-8")

    fragment_pair_counts: Counter[str] = Counter()
    fragment_card_counts: Counter[str] = Counter()
    card_pair_counts: Counter[str] = Counter()
    mechanic_pair_counts: Counter[str] = Counter()
    detail_breakdown: Counter[str] = Counter()
    example_pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in recovery.rows:
        detail_breakdown[row.detail] += 1
        if row.stage.value != "compiler_unsupported":
            continue
        names_key = " + ".join(sorted(row.names))
        card_pair_counts[names_key] += 1
        families = tag_mechanic(names_key, row.detail)
        for fam in families:
            mechanic_pair_counts[fam] += 1
        if len(example_pairs[families[0]]) < 3:
            example_pairs[families[0]].append(
                {"variant_id": row.variant_id, "names": row.names, "detail": row.detail}
            )

        for name in row.names:
            card_pair_counts[name] += 1
            sem = cards_by_name.get(name.casefold())
            if sem is None:
                continue
            for frag in sem.unsupported_fragments:
                norm = _normalize_fragment(frag)
                fragment_pair_counts[norm] += 1
                fragment_card_counts[f"{name}::{norm}"] += 1

    unresolved_dfc = [n for n in unresolved_names if "//" in n]
    unresolved_other = [n for n in unresolved_names if "//" not in n]

    return {
        "inputs": {
            "variants_path": str(variants_path),
            "variant_count": len(selected),
            "unique_card_names": len(all_names),
            "scryfall_snapshot_hash": scryfall_manifest.get("oracle_snapshot_hash"),
            "spellbook_pages_note": "Use data/spellbook/latest manifest for Spellbook hash",
        },
        "recovery_counts": recovery.counts.model_dump(),
        "detail_breakdown": dict(detail_breakdown.most_common()),
        "top_cards_in_failed_pairs": card_pair_counts.most_common(25),
        "top_unsupported_fragments": fragment_pair_counts.most_common(30),
        "mechanic_family_pressure": mechanic_pair_counts.most_common(),
        "mechanic_examples": {k: v[:3] for k, v in example_pairs.items()},
        "unresolved_names": {
            "dfc_count": len(unresolved_dfc),
            "other_count": len(unresolved_other),
            "dfc_top": Counter(unresolved_dfc).most_common(15),
            "other_top": Counter(unresolved_other).most_common(10),
        },
        "curriculum_recommendations": _recommendations(
            fragment_pair_counts, mechanic_pair_counts, recovery.counts.eligible
        ),
    }


def _recommendations(
    fragments: Counter[str],
    mechanics: Counter[str],
    eligible: int,
) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    if eligible == 0:
        recs.append(
            {
                "priority": "P0",
                "action": "Expand deterministic patterns until eligible >= 1 (M4 gate)",
                "rationale": "Recall undefined while eligible=0",
            }
        )
    for rank, (family, count) in enumerate(mechanics.most_common(5), start=1):
        recs.append(
            {
                "priority": f"P{rank}",
                "action": f"Compiler curriculum: {family} ({count} failed pairs tagged)",
                "rationale": "Highest Spellbook conventional-two-card pressure in live diagnostic",
            }
        )
    for rank, (frag, count) in enumerate(fragments.most_common(5), start=1):
        recs.append(
            {
                "priority": f"fragment-{rank}",
                "action": f"Pattern for: {frag[:100]}",
                "rationale": f"Appears in {count} pair compilations",
            }
        )
    return recs


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["recovery_counts"]
    lines = [
        "# Spellbook compiler priority report (live diagnostic)",
        "",
        "## Recovery summary",
        "",
        f"- Selected pairs: **{counts['selected']}**",
        f"- Compiled: **{counts['compiled']}**",
        f"- Supported / eligible / rediscovered: **{counts['supported']}** / "
        f"**{counts['eligible']}** / **{counts['rediscovered']}**",
        f"- Compiler unsupported: **{counts['compiler_unsupported']}**",
        "",
        "## Detail breakdown",
        "",
    ]
    for detail, n in report["detail_breakdown"].items():
        lines.append(f"- `{detail}`: {n}")
    lines.extend(["", "## Mechanic family pressure (heuristic tags)", ""])
    for family, n in report["mechanic_family_pressure"]:
        lines.append(f"- **{family}**: {n} pairs")
        for ex in report["mechanic_examples"].get(family, []):
            lines.append(f"  - e.g. {' + '.join(ex['names'])}")
    lines.extend(["", "## Top unsupported Oracle fragments", ""])
    for frag, n in report["top_unsupported_fragments"][:15]:
        lines.append(f"- ({n}) `{frag}`")
    lines.extend(["", "## Top cards appearing in failed pairs", ""])
    for name, n in report["top_cards_in_failed_pairs"][:15]:
        if " + " not in name:
            lines.append(f"- {name}: {n}")
    unresolved = report["unresolved_names"]
    lines.extend(
        [
            "",
            "## Unresolved card names",
            "",
            f"- DFC / split names: {unresolved['dfc_count']}",
            f"- Other unresolved: {unresolved['other_count']}",
            "",
            "## Curriculum recommendations",
            "",
        ]
    )
    for rec in report["curriculum_recommendations"]:
        lines.append(f"- **{rec['priority']}** — {rec['action']} ({rec['rationale']})")
    lines.append("")
    lines.append(
        "_Live diagnostic only — not a certified baseline. "
        "See `docs/EVALUATION.md` for denominator rules._"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", type=Path, default=DEFAULT_VARIANTS)
    parser.add_argument("--scryfall-dir", type=Path, default=DEFAULT_SCRYFALL)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--recovery-out", type=Path, default=DEFAULT_RECOVERY)
    parser.add_argument("--no-recovery", action="store_true")
    args = parser.parse_args()

    if not args.variants.exists():
        raise SystemExit(f"missing variants: {args.variants}")
    if not args.scryfall_dir.exists():
        raise SystemExit(f"missing scryfall snapshot: {args.scryfall_dir}")

    report = run_analysis(
        args.variants,
        args.scryfall_dir,
        write_recovery=None if args.no_recovery else args.recovery_out,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_json": str(args.out_json), "counts": report["recovery_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
