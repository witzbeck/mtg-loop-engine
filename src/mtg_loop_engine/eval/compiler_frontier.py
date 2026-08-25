"""Compiler frontier: rank missing semantics by COMPLETE / pair unlock value.

Live diagnostic for M5.1. Pair unlock here means counterfactual both-COMPLETE
eligibility — not rediscovery (search/verifier). Optional simulation of
rediscovery stays behind a separate flag at the script layer.
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import StrEnum
from typing import Any, Iterable

from pydantic import BaseModel, Field

from mtg_loop_engine.corpus.gold_extended.oracle_gaps import (
    OracleGap,
    oracle_gap_catalog,
)
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics


class GapKind(StrEnum):
    """Interpretable cost of closing one unsupported fragment."""

    PATTERN_EXISTING_PHYSICS = "pattern_existing_physics"
    REUSABLE_NEW_PRIMITIVE = "reusable_new_primitive"
    SUBSTANTIAL_RULES = "substantial_rules"


class FrontierTier(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


# High rules-cost families — prefer pattern-only or reusable primitives first.
_SUBSTANTIAL_NEEDLES: tuple[str, ...] = (
    "copy target",
    "copy that",
    "create a token that's a copy",
    "imprint",
    "exile target",
    "return it to the battlefield",
    "return that card to the battlefield",
    "blink",
    "soulbond",
    "additional combat",
    "extra combat",
    "untap all attacking",
    "delayed",
    "when that creature dies this turn",
    "buyback",
    "cascade",
    "suspend",
    "transform",
    "meld",
)

# Clause shapes that usually map onto existing IR / proof-irrelevant statics.
_EXISTING_PHYSICS_NEEDLES: tuple[str, ...] = (
    "{t}: add",
    "add {",
    "add one mana",
    "untap target",
    "untap this",
    "tap target",
    "tap an untapped",
    "deals ",
    "deal 1 damage",
    "create a",
    "token",
    "gain life",
    "loses life",
    "draw a card",
    "sacrifice a creature",
    "sacrifice this",
    "+1/+1 counter",
    "-1/-1 counter",
    "enchant ",
    "flying",
    "haste",
    "vigilance",
    "trample",
    "reach",
    "defender",
    "flash",
    "devoid",
    "other creatures you control get",
    "creatures you control get",
    "equipped creature gets",
    "enchanted creature gets",
)


def normalize_fragment(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed[:120]


def distance_to_complete(sem: CardSemantics) -> int:
    """Number of unsupported Oracle clauses blocking COMPLETE."""
    if (
        sem.coverage is SemanticCoverage.COMPLETE
        and not sem.unsupported_fragments
    ):
        return 0
    return len(sem.unsupported_fragments)


def unique_unsupported(sem: CardSemantics) -> list[str]:
    """Deduped normalized unsupported fragments (stable order)."""
    seen: set[str] = set()
    out: list[str] = []
    for frag in sem.unsupported_fragments:
        norm = normalize_fragment(frag)
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def classify_gap(fragment: str) -> GapKind:
    """Heuristic gap cost — interpretable, not a scalar score."""
    blob = normalize_fragment(fragment)
    if any(n in blob for n in _SUBSTANTIAL_NEEDLES):
        return GapKind.SUBSTANTIAL_RULES
    if any(n in blob for n in _EXISTING_PHYSICS_NEEDLES):
        return GapKind.PATTERN_EXISTING_PHYSICS
    return GapKind.REUSABLE_NEW_PRIMITIVE


def is_complete(sem: CardSemantics) -> bool:
    return distance_to_complete(sem) == 0


def would_be_complete_after(
    sem: CardSemantics,
    closed_norms: set[str],
) -> bool:
    """True if removing closed fragment norms leaves no unsupported clauses."""
    remaining = [
        f
        for f in sem.unsupported_fragments
        if normalize_fragment(f) not in closed_norms
    ]
    return len(remaining) == 0


def cards_unlocked_by_fragment(
    cards: dict[str, CardSemantics],
    fragment_norm: str,
) -> list[str]:
    """Names that transition incomplete → COMPLETE when ``fragment_norm`` closes."""
    closed = {fragment_norm}
    unlocked: list[str] = []
    for name, sem in sorted(cards.items(), key=lambda kv: kv[0].casefold()):
        if is_complete(sem):
            continue
        if fragment_norm not in unique_unsupported(sem):
            continue
        if would_be_complete_after(sem, closed):
            unlocked.append(name)
    return unlocked


def pairs_unlocked_both_complete(
    pairs: Iterable[tuple[str, str]],
    cards: dict[str, CardSemantics],
    fragment_norm: str,
) -> list[tuple[str, str]]:
    """Conventional pairs that become both-COMPLETE after closing ``fragment_norm``.

    Already both-COMPLETE pairs are excluded. A pair counts only when both
    participants are COMPLETE after the counterfactual and at least one card
    needed the closed fragment (otherwise the pair was already eligible).
    """
    closed = {fragment_norm}
    unlocked: list[tuple[str, str]] = []
    for left, right in pairs:
        a = cards.get(left)
        b = cards.get(right)
        if a is None or b is None:
            continue
        before_both = is_complete(a) and is_complete(b)
        if before_both:
            continue
        after_a = is_complete(a) or would_be_complete_after(a, closed)
        after_b = is_complete(b) or would_be_complete_after(b, closed)
        if not (after_a and after_b):
            continue
        needed = (
            fragment_norm in unique_unsupported(a)
            or fragment_norm in unique_unsupported(b)
        )
        if not needed:
            continue
        unlocked.append((left, right))
    return unlocked


def tier_for_fragment(
    *,
    gap_kind: GapKind,
    cards_unlocked: int,
    sole_gap_cards: int,
) -> FrontierTier:
    """Coarse tier from interpretable signals (no weighted score)."""
    if gap_kind is GapKind.SUBSTANTIAL_RULES:
        return FrontierTier.P2
    if sole_gap_cards == 0 and cards_unlocked == 0:
        # Only appears on multi-gap cards; closing it alone completes nothing.
        return FrontierTier.P2
    if gap_kind is GapKind.PATTERN_EXISTING_PHYSICS and sole_gap_cards > 0:
        return FrontierTier.P0
    if gap_kind is GapKind.PATTERN_EXISTING_PHYSICS and cards_unlocked > 0:
        return FrontierTier.P1
    if gap_kind is GapKind.REUSABLE_NEW_PRIMITIVE and sole_gap_cards > 0:
        return FrontierTier.P1
    return FrontierTier.P2


class GapDetail(BaseModel):
    fragment: str
    raw_examples: list[str] = Field(default_factory=list)
    gap_kind: GapKind


class CardFrontier(BaseModel):
    name: str
    oracle_id: str | None = None
    coverage: str
    distance_to_complete: int
    unsupported_fragments: list[str] = Field(default_factory=list)
    gaps: list[GapDetail] = Field(default_factory=list)
    spellbook_pair_count: int = 0
    oracle_gap_ids: list[str] = Field(default_factory=list)


class FragmentFrontier(BaseModel):
    fragment: str
    gap_kind: GapKind
    tier: FrontierTier
    cards_unlocked: int
    pairs_unlocked_both_complete: int
    sole_gap_cards: int
    cards_containing: int
    representative_cards: list[str] = Field(default_factory=list)
    representative_pairs: list[str] = Field(default_factory=list)


class OracleGapFrontier(BaseModel):
    """Staged gold remainders — always visible, no privileged sequencing."""

    proposed_gold_id: str
    left_name: str
    right_name: str
    blockers: list[str]
    notes: str = ""
    left: CardFrontier | None = None
    right: CardFrontier | None = None
    both_complete: bool = False


class CompilerFrontierReport(BaseModel):
    assumptions: list[str] = Field(default_factory=list)
    complete_cards: int = 0
    partial_cards: int = 0
    unresolved_cards: int = 0
    cards: list[CardFrontier] = Field(default_factory=list)
    fragments: list[FragmentFrontier] = Field(default_factory=list)
    tiers: dict[str, list[FragmentFrontier]] = Field(default_factory=dict)
    oracle_gaps: list[OracleGapFrontier] = Field(default_factory=list)


_DEFAULT_ASSUMPTIONS = [
    "pair_unlock = counterfactual both-COMPLETE eligibility, not rediscovery",
    "gap_kind is a heuristic over Oracle text; humans choose curriculum slices",
    "tiers are coarse (P0/P1/P2); no weighted scalar score",
]


def _card_row(
    name: str,
    sem: CardSemantics,
    *,
    pair_count: int,
    gap_ids: list[str],
) -> CardFrontier:
    frags = unique_unsupported(sem)
    gaps = [
        GapDetail(
            fragment=f,
            raw_examples=[
                raw
                for raw in sem.unsupported_fragments
                if normalize_fragment(raw) == f
            ][:2],
            gap_kind=classify_gap(f),
        )
        for f in frags
    ]
    return CardFrontier(
        name=name,
        oracle_id=sem.oracle_id,
        coverage=sem.coverage.value,
        distance_to_complete=distance_to_complete(sem),
        unsupported_fragments=frags,
        gaps=gaps,
        spellbook_pair_count=pair_count,
        oracle_gap_ids=gap_ids,
    )


def build_frontier(
    cards_by_name: dict[str, CardSemantics],
    conventional_pairs: Iterable[tuple[str, str]],
    *,
    unresolved_names: Iterable[str] = (),
    oracle_gaps: list[OracleGap] | None = None,
    max_representatives: int = 5,
) -> CompilerFrontierReport:
    """Build frontier from already-compiled Spellbook (+ optional gap) cards.

    ``cards_by_name`` keys should be display names (not casefolded). Lookups
    are case-insensitive via an internal index.
    """
    gaps = oracle_gaps if oracle_gaps is not None else oracle_gap_catalog()
    pair_list = [(a, b) for a, b in conventional_pairs]

    by_fold: dict[str, tuple[str, CardSemantics]] = {}
    for name, sem in cards_by_name.items():
        by_fold[name.casefold()] = (name, sem)

    pair_counts: dict[str, int] = defaultdict(int)
    for a, b in pair_list:
        pair_counts[a.casefold()] += 1
        pair_counts[b.casefold()] += 1

    gap_ids_by_name: dict[str, list[str]] = defaultdict(list)
    for gap in gaps:
        for n in (gap.left_name, gap.right_name):
            gap_ids_by_name[n.casefold()].append(gap.proposed_gold_id)

    card_rows: list[CardFrontier] = []
    for fold, (name, sem) in sorted(by_fold.items(), key=lambda kv: kv[0]):
        card_rows.append(
            _card_row(
                name,
                sem,
                pair_count=pair_counts.get(fold, 0),
                gap_ids=list(gap_ids_by_name.get(fold, [])),
            )
        )

    complete = sum(1 for c in card_rows if c.distance_to_complete == 0)
    partial = sum(1 for c in card_rows if c.distance_to_complete > 0)
    unresolved = len(list(unresolved_names))

    # Fragment → cards that contain it / sole-gap cards
    containing: dict[str, list[str]] = defaultdict(list)
    sole_gap: dict[str, list[str]] = defaultdict(list)
    gap_kind_for: dict[str, GapKind] = {}
    for row in card_rows:
        for g in row.gaps:
            containing[g.fragment].append(row.name)
            gap_kind_for[g.fragment] = g.gap_kind
        if row.distance_to_complete == 1 and row.unsupported_fragments:
            sole_gap[row.unsupported_fragments[0]].append(row.name)

    cards_for_unlock = {disp: sem for disp, sem in (by_fold[k] for k in by_fold)}

    resolved_pairs: list[tuple[str, str]] = []
    for a, b in pair_list:
        sa = by_fold.get(a.casefold())
        sb = by_fold.get(b.casefold())
        if sa is None or sb is None:
            continue
        resolved_pairs.append((sa[0], sb[0]))

    fragment_rows: list[FragmentFrontier] = []
    for frag, names in containing.items():
        unlocked_cards = cards_unlocked_by_fragment(cards_for_unlock, frag)
        unlocked_pairs = pairs_unlocked_both_complete(
            resolved_pairs, cards_for_unlock, frag
        )
        kind = gap_kind_for.get(frag, classify_gap(frag))
        sole = sole_gap.get(frag, [])
        tier = tier_for_fragment(
            gap_kind=kind,
            cards_unlocked=len(unlocked_cards),
            sole_gap_cards=len(sole),
        )
        fragment_rows.append(
            FragmentFrontier(
                fragment=frag,
                gap_kind=kind,
                tier=tier,
                cards_unlocked=len(unlocked_cards),
                pairs_unlocked_both_complete=len(unlocked_pairs),
                sole_gap_cards=len(sole),
                cards_containing=len(names),
                representative_cards=(unlocked_cards or names)[:max_representatives],
                representative_pairs=[
                    f"{x} + {y}" for x, y in unlocked_pairs[:max_representatives]
                ],
            )
        )

    fragment_rows.sort(
        key=lambda r: (
            -r.pairs_unlocked_both_complete,
            -r.cards_unlocked,
            -r.sole_gap_cards,
            r.fragment,
        )
    )

    tiers: dict[str, list[FragmentFrontier]] = {
        FrontierTier.P0.value: [],
        FrontierTier.P1.value: [],
        FrontierTier.P2.value: [],
    }
    for row in fragment_rows:
        tiers[row.tier.value].append(row)

    oracle_gap_rows: list[OracleGapFrontier] = []
    card_by_fold = {c.name.casefold(): c for c in card_rows}
    for gap in gaps:
        left = card_by_fold.get(gap.left_name.casefold())
        right = card_by_fold.get(gap.right_name.casefold())
        both = (
            left is not None
            and right is not None
            and left.distance_to_complete == 0
            and right.distance_to_complete == 0
        )
        oracle_gap_rows.append(
            OracleGapFrontier(
                proposed_gold_id=gap.proposed_gold_id,
                left_name=gap.left_name,
                right_name=gap.right_name,
                blockers=list(gap.blockers),
                notes=gap.notes,
                left=left,
                right=right,
                both_complete=both,
            )
        )

    return CompilerFrontierReport(
        assumptions=list(_DEFAULT_ASSUMPTIONS),
        complete_cards=complete,
        partial_cards=partial,
        unresolved_cards=unresolved,
        cards=card_rows,
        fragments=fragment_rows,
        tiers=tiers,
        oracle_gaps=oracle_gap_rows,
    )


def render_frontier_markdown(report: CompilerFrontierReport) -> str:
    lines = [
        "# Compiler frontier (live diagnostic)",
        "",
        "## Assumptions",
        "",
    ]
    for a in report.assumptions:
        lines.append(f"- {a}")
    lines.extend(
        [
            "",
            "## Pool",
            "",
            f"- COMPLETE cards: **{report.complete_cards}**",
            f"- Partial (distance ≥ 1): **{report.partial_cards}**",
            f"- Unresolved names: **{report.unresolved_cards}**",
            "",
        ]
    )
    for tier in (FrontierTier.P0, FrontierTier.P1, FrontierTier.P2):
        rows = report.tiers.get(tier.value, [])
        lines.extend([f"## {tier.value}", ""])
        if not rows:
            lines.append("_None._")
            lines.append("")
            continue
        lines.append(
            "| Fragment | Kind | Cards unlocked | Pairs both-COMPLETE | Sole-gap | Examples |"
        )
        lines.append("| --- | --- | ---: | ---: | ---: | --- |")
        for r in rows[:25]:
            examples = ", ".join(r.representative_cards[:3]) or "—"
            frag = r.fragment.replace("|", "\\|")[:80]
            lines.append(
                f"| `{frag}` | {r.gap_kind.value} | {r.cards_unlocked} | "
                f"{r.pairs_unlocked_both_complete} | {r.sole_gap_cards} | {examples} |"
            )
        lines.append("")

    lines.extend(["## Staged oracle_gaps (compete with frontier)", ""])
    if not report.oracle_gaps:
        lines.append("_None catalogued._")
    else:
        for g in report.oracle_gaps:
            ld = g.left.distance_to_complete if g.left else "?"
            rd = g.right.distance_to_complete if g.right else "?"
            lines.append(
                f"- **{g.proposed_gold_id}**: {g.left_name} (d={ld}) + "
                f"{g.right_name} (d={rd}); both_COMPLETE={g.both_complete}"
            )
            if g.left and g.left.unsupported_fragments:
                lines.append(
                    f"  - {g.left_name} gaps: "
                    + "; ".join(f"`{f}`" for f in g.left.unsupported_fragments[:3])
                )
            if g.right and g.right.unsupported_fragments:
                lines.append(
                    f"  - {g.right_name} gaps: "
                    + "; ".join(f"`{f}`" for f in g.right.unsupported_fragments[:3])
                )
            for b in g.blockers:
                lines.append(f"  - blocker: {b}")
    lines.append("")
    lines.append(
        "_Live diagnostic only — not a certified baseline. "
        "`pair_unlock` ≠ rediscovery._"
    )
    return "\n".join(lines) + "\n"


def frontier_to_jsonable(report: CompilerFrontierReport) -> dict[str, Any]:
    return report.model_dump(mode="json")


__all__ = [
    "CardFrontier",
    "CompilerFrontierReport",
    "FragmentFrontier",
    "FrontierTier",
    "GapDetail",
    "GapKind",
    "OracleGapFrontier",
    "build_frontier",
    "cards_unlocked_by_fragment",
    "classify_gap",
    "distance_to_complete",
    "frontier_to_jsonable",
    "is_complete",
    "normalize_fragment",
    "pairs_unlocked_both_complete",
    "render_frontier_markdown",
    "tier_for_fragment",
    "unique_unsupported",
    "would_be_complete_after",
]
