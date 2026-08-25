"""Contracts for M5.1 compiler-frontier ranking inputs."""

from __future__ import annotations

from mtg_loop_engine.corpus.gold_extended.oracle_gaps import OracleGap
from mtg_loop_engine.eval.compiler_frontier import (
    FrontierTier,
    GapKind,
    build_frontier,
    cards_unlocked_by_fragment,
    classify_gap,
    distance_to_complete,
    normalize_fragment,
    pairs_unlocked_both_complete,
    tier_for_fragment,
)
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics


def _card(
    name: str,
    *,
    unsupported: list[str] | None = None,
    coverage: SemanticCoverage | None = None,
) -> CardSemantics:
    frags = unsupported or []
    if coverage is None:
        coverage = (
            SemanticCoverage.COMPLETE
            if not frags
            else SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
        )
    return CardSemantics(
        oracle_id=f"oid:{name.casefold()}",
        name=name,
        types=["Creature"],
        abilities=[],
        unsupported_fragments=frags,
        coverage=coverage,
    )


def test_one_missing_pattern_is_distance_1():
    sem = _card("Alpha", unsupported=["{T}: Add {G} for each Elf you control"])
    assert distance_to_complete(sem) == 1


def test_two_independent_gaps_are_distance_2():
    sem = _card(
        "Beta",
        unsupported=[
            "{T}: Add {G} for each Elf you control",
            "Soulbond",
        ],
    )
    assert distance_to_complete(sem) == 2


def test_closing_shared_gap_unlocks_correct_card_count():
    cards = {
        "A": _card("A", unsupported=["{T}: Add {G} for each creature you control"]),
        "B": _card("B", unsupported=["{T}: Add {G} for each creature you control"]),
        "C": _card(
            "C",
            unsupported=[
                "{T}: Add {G} for each creature you control",
                "Whenever you gain life, draw a card",
            ],
        ),
        "Done": _card("Done"),
    }
    frag = normalize_fragment("{T}: Add {G} for each creature you control")
    unlocked = cards_unlocked_by_fragment(cards, frag)
    assert set(unlocked) == {"A", "B"}
    assert "C" not in unlocked
    assert "Done" not in unlocked


def test_pair_unlocks_only_when_both_become_complete():
    cards = {
        "Left": _card("Left", unsupported=["untap target creature"]),
        "Right": _card("Right", unsupported=["untap target creature"]),
        "Partial": _card(
            "Partial",
            unsupported=["untap target creature", "soulbond (this creature)"],
        ),
        "Complete": _card("Complete"),
    }
    frag = normalize_fragment("untap target creature")
    pairs = [
        ("Left", "Right"),
        ("Left", "Partial"),
        ("Left", "Complete"),
        ("Complete", "Complete"),
    ]
    unlocked = pairs_unlocked_both_complete(pairs, cards, frag)
    assert ("Left", "Right") in unlocked
    assert ("Left", "Complete") in unlocked
    assert ("Left", "Partial") not in unlocked


def test_already_complete_pair_does_not_inflate_unlock():
    cards = {
        "X": _card("X"),
        "Y": _card("Y"),
        "Z": _card("Z", unsupported=["{T}: Add {G}"]),
    }
    frag = normalize_fragment("{T}: Add {G}")
    unlocked = pairs_unlocked_both_complete([("X", "Y"), ("X", "Z")], cards, frag)
    assert ("X", "Y") not in unlocked
    assert ("X", "Z") in unlocked


def test_rules_cost_classification_changes_tier():
    assert classify_gap("{T}: Add {G} for each Elf") is GapKind.PATTERN_EXISTING_PHYSICS
    assert (
        classify_gap("Create a token that's a copy of target creature")
        is GapKind.SUBSTANTIAL_RULES
    )
    assert classify_gap("Station (spacecraft)") is GapKind.REUSABLE_NEW_PRIMITIVE

    assert (
        tier_for_fragment(
            gap_kind=GapKind.PATTERN_EXISTING_PHYSICS,
            cards_unlocked=3,
            sole_gap_cards=3,
        )
        is FrontierTier.P0
    )
    assert (
        tier_for_fragment(
            gap_kind=GapKind.REUSABLE_NEW_PRIMITIVE,
            cards_unlocked=2,
            sole_gap_cards=2,
        )
        is FrontierTier.P1
    )
    assert (
        tier_for_fragment(
            gap_kind=GapKind.SUBSTANTIAL_RULES,
            cards_unlocked=5,
            sole_gap_cards=5,
        )
        is FrontierTier.P2
    )
    assert (
        tier_for_fragment(
            gap_kind=GapKind.PATTERN_EXISTING_PHYSICS,
            cards_unlocked=0,
            sole_gap_cards=0,
        )
        is FrontierTier.P2
    )


def test_oracle_gaps_are_visible_in_frontier():
    cards = {
        "Saffi Eriksdotter": _card(
            "Saffi Eriksdotter",
            unsupported=["Sacrifice this creature: When target creature dies this turn, return it"],
        ),
        "Crypt Champion": _card(
            "Crypt Champion",
            unsupported=["When this creature enters, return target creature card"],
        ),
        "Mikaeus, the Unhallowed": _card(
            "Mikaeus, the Unhallowed",
            unsupported=["Other non-Human creatures you control get +1/+1 and have undying"],
        ),
        "Triskelion": _card("Triskelion"),
        "Partner": _card("Partner"),
    }
    gaps = [
        OracleGap(
            proposed_gold_id="core_saffi_champion",
            left_name="Saffi Eriksdotter",
            right_name="Crypt Champion",
            blockers=("delayed trigger",),
        ),
        OracleGap(
            proposed_gold_id="core_mikaeus_triskelion",
            left_name="Mikaeus, the Unhallowed",
            right_name="Triskelion",
            blockers=("grant/anthem",),
        ),
    ]
    report = build_frontier(
        cards,
        [("Saffi Eriksdotter", "Crypt Champion"), ("Partner", "Triskelion")],
        oracle_gaps=gaps,
    )
    ids = {g.proposed_gold_id for g in report.oracle_gaps}
    assert ids == {"core_saffi_champion", "core_mikaeus_triskelion"}
    saffi = next(g for g in report.oracle_gaps if g.proposed_gold_id == "core_saffi_champion")
    assert saffi.left is not None
    assert saffi.left.distance_to_complete >= 1
    assert saffi.both_complete is False
    mikaeus = next(
        g for g in report.oracle_gaps if g.proposed_gold_id == "core_mikaeus_triskelion"
    )
    assert mikaeus.right is not None
    assert mikaeus.right.distance_to_complete == 0
    # Gap cards appear in the card census with oracle_gap_ids stamped.
    saffi_card = next(c for c in report.cards if c.name == "Saffi Eriksdotter")
    assert "core_saffi_champion" in saffi_card.oracle_gap_ids


def test_frontier_sorts_by_pair_unlock_not_fragment_frequency():
    """A rare fragment that completes pairs outranks a frequent zero-unlock fragment."""
    common = "Whenever a creature dies, you may pay {1}. If you do, draw a card."
    useful = "{T}: Add {G} for each creature you control"
    cards = {
        "Hub": _card("Hub"),
        "RareA": _card("RareA", unsupported=[useful]),
        "RareB": _card("RareB", unsupported=[useful]),
        "Noisy1": _card("Noisy1", unsupported=[common, "soulbond"]),
        "Noisy2": _card("Noisy2", unsupported=[common, "soulbond"]),
        "Noisy3": _card("Noisy3", unsupported=[common, "soulbond"]),
    }
    pairs = [
        ("RareA", "Hub"),
        ("RareB", "Hub"),
        ("Noisy1", "Hub"),
        ("Noisy2", "Hub"),
        ("Noisy3", "Hub"),
    ]
    report = build_frontier(cards, pairs, oracle_gaps=[])
    useful_n = normalize_fragment(useful)
    common_n = normalize_fragment(common)
    by_frag = {f.fragment: f for f in report.fragments}
    assert by_frag[useful_n].pairs_unlocked_both_complete == 2
    assert by_frag[common_n].pairs_unlocked_both_complete == 0
    assert by_frag[useful_n].cards_unlocked == 2
    # Ranking: useful before common (pair unlock primary).
    order = [f.fragment for f in report.fragments]
    assert order.index(useful_n) < order.index(common_n)
