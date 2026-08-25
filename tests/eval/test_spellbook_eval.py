"""Spellbook-shaped reference recovery on committed sample fixtures."""

from pathlib import Path

from mtg_loop_engine.eval.schema import FailureStage
from mtg_loop_engine.eval.spellbook_eval import (
    evaluate_reference_subset,
    load_variant_jsonl,
)

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "eval"
    / "fixtures"
    / "spellbook_conventional_sample.jsonl"
)


def test_sample_recovers_gold_pairs_and_fails_unsupported():
    report = evaluate_reference_subset(load_variant_jsonl(SAMPLE))
    assert report.counts.selected == 3
    stages = {row.variant_id: row.stage for row in report.rows}
    assert stages["ref-basalt-grounds"] == FailureStage.RECOVERED
    assert stages["ref-alarm-tapper"] == FailureStage.RECOVERED
    assert stages["ref-isochron"] == FailureStage.COMPILER_UNSUPPORTED
    assert report.counts.eligible == 2
    assert report.counts.rediscovered == 2
    assert report.counts.recall_eligible == 1.0


def test_recovery_stages_join_miss_and_search_miss():
    """Synthetic COMPLETE cards: no join → JOIN_MISS; join without accept → SEARCH_MISS."""
    from mtg_loop_engine.corpus.gold_core.cases import ASHNOD, BASALT
    from mtg_loop_engine.semantics.ir import (
        ActivatedAbility,
        AddManaEffect,
        CardSemantics,
        ManaAmount,
        TapCost,
    )

    rock_a = CardSemantics(
        oracle_id="oracle:rock-a",
        name="Barren Rock A",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(colorless=1))],
                is_mana_ability=True,
            )
        ],
    )
    rock_b = CardSemantics(
        oracle_id="oracle:rock-b",
        name="Barren Rock B",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(colorless=1))],
                is_mana_ability=True,
            )
        ],
    )
    lookup = {
        rock_a.name.casefold(): rock_a,
        rock_b.name.casefold(): rock_b,
        BASALT.name.casefold(): BASALT,
        ASHNOD.name.casefold(): ASHNOD,
    }
    variants = [
        {
            "id": "syn-join-miss",
            "uses": [{"card": {"name": rock_a.name}}, {"card": {"name": rock_b.name}}],
            "requires": [],
            "produces": [{"name": "Infinite colorless mana"}],
        },
        {
            "id": "syn-search-miss",
            "uses": [
                {"card": {"name": BASALT.name}},
                {"card": {"name": ASHNOD.name}},
            ],
            "requires": [],
            "produces": [{"name": "Infinite colorless mana"}],
        },
    ]
    report = evaluate_reference_subset(variants, cards_by_name=lookup)
    stages = {row.variant_id: row.stage for row in report.rows}
    assert stages["syn-join-miss"] == FailureStage.CANDIDATE_JOIN_MISS
    assert stages["syn-search-miss"] == FailureStage.SEARCH_MISS
    assert report.counts.join_miss == 1
    assert report.counts.search_miss == 1


def test_gold_extra_adjudications_cover_discovered_extras():
    from mtg_loop_engine.eval.gold_extras import (
        GOLD_EXTRA_ADJUDICATIONS,
        collect_gold_pool_extras,
    )

    extras = collect_gold_pool_extras()
    keys = {frozenset({r.left_id, r.right_id}) for r in extras}
    assert keys == set(GOLD_EXTRA_ADJUDICATIONS)
    assert len(extras) == 11
