"""Spellbook conventional two-card reference recovery (no pair labels into search)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mtg_loop_engine.benchmark.spellbook import is_conventional_two_card
from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.eval.metrics import RecoveryCounts, RecoveryReport, RecoveryRow
from mtg_loop_engine.eval.schema import FailureStage
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def variant_id(variant: dict[str, Any]) -> str:
    return str(variant.get("id") or variant.get("identity") or json.dumps(variant, sort_keys=True)[:80])


def variant_card_names(variant: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for use in variant.get("uses") or variant.get("cards") or []:
        if isinstance(use, dict):
            card = use.get("card") or use
            name = card.get("name")
            if name:
                names.append(str(name))
        else:
            names.append(str(use))
    return names


def load_variant_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def fixtures_by_name() -> dict[str, CardSemantics]:
    out: dict[str, CardSemantics] = {}
    for fixture in GOLD_ORACLE_FIXTURES.values():
        report = compile_oracle_text(
            oracle_id=fixture.oracle_id,
            name=fixture.name,
            oracle_text=fixture.oracle_text,
            types=fixture.types,
        )
        out[fixture.name.casefold()] = report.semantics
    return out


def compile_card(oracle_id: str, name: str, oracle_text: str, types: list[str]) -> CardSemantics:
    return compile_oracle_text(
        oracle_id=oracle_id,
        name=name,
        oracle_text=oracle_text,
        types=types,
    ).semantics


def evaluate_reference_subset(
    variants: list[dict[str, Any]],
    *,
    cards_by_name: dict[str, CardSemantics] | None = None,
    max_depth: int = 6,
) -> RecoveryReport:
    """Score conventional two-card rows. Pair labels are not passed into search."""
    lookup = cards_by_name or fixtures_by_name()
    selected = [v for v in variants if is_conventional_two_card(v)]
    counts = RecoveryCounts(selected=len(selected))
    rows: list[RecoveryRow] = []

    pool: dict[str, CardSemantics] = {}
    eligible_pairs: list[tuple[str, frozenset[str], list[str]]] = []

    for variant in selected:
        names = variant_card_names(variant)
        vid = variant_id(variant)
        compiled: list[CardSemantics] = []
        missing = []
        for name in names:
            card = lookup.get(name.casefold())
            if card is None:
                missing.append(name)
            else:
                compiled.append(card)
        if missing or len(compiled) != 2:
            counts.compiler_unsupported += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.COMPILER_UNSUPPORTED,
                    detail=f"unresolved or uncompiled: {missing}",
                )
            )
            continue
        counts.compiled += 1
        if any(c.relevant_unsupported() for c in compiled):
            counts.compiler_unsupported += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.COMPILER_UNSUPPORTED,
                    detail="proof-relevant unsupported fragments",
                )
            )
            continue
        if any(c.coverage != SemanticCoverage.COMPLETE for c in compiled):
            counts.compiler_unsupported += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.COMPILER_UNSUPPORTED,
                    detail="incomplete coverage",
                )
            )
            continue
        counts.supported += 1
        counts.eligible += 1
        for card in compiled:
            pool[card.oracle_id] = card
        eligible_pairs.append(
            (vid, frozenset(c.oracle_id for c in compiled), names)
        )

    index = InteractionIndex(list(pool.values()))
    joined = {
        frozenset({p.left_id, p.right_id}): p for p in index.candidate_pairs()
    }

    for vid, key, names in eligible_pairs:
        pair = joined.get(key)
        if pair is None:
            counts.join_miss += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.CANDIDATE_JOIN_MISS,
                    detail="interaction index did not propose this pair",
                )
            )
            continue
        left = pool[pair.left_id]
        right = pool[pair.right_id]
        found = explore_pair(left, right, max_depth=max_depth)
        if found is None:
            counts.search_miss += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.SEARCH_MISS,
                    detail="bounded search returned no verifier-accepted witness",
                )
            )
            continue
        analysis = analyze_prerequisites(found.witness)
        if not analysis.strict_two_card:
            counts.classification_mismatch += 1
            rows.append(
                RecoveryRow(
                    variant_id=vid,
                    names=names,
                    stage=FailureStage.PREREQUISITE_MISMATCH,
                    detail=(
                        f"recovered but not strict two-card "
                        f"(participants={analysis.essential_functional_count})"
                    ),
                )
            )
            continue
        counts.rediscovered += 1
        rows.append(
            RecoveryRow(
                variant_id=vid,
                names=names,
                stage=FailureStage.RECOVERED,
                detail=",".join(pair.reasons),
            )
        )

    return RecoveryReport(counts=counts, rows=rows)
