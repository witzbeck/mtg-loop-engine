"""Real-Oracle Altar + zone-recursion: live cast-from-GY and activated-return curriculum."""

from mtg_loop_engine.eval.spellbook_eval import compile_card, evaluate_reference_subset
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ActivatedAbility, AddManaEffect, ManaAmount
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_card(
        f"oracle:{key.lower().replace(' ', '-')}",
        row.name,
        row.oracle_text,
        row.types,
    )


def test_real_altar_produces_any_color_not_generic():
    altar = _compile("Phyrexian Altar")
    assert altar.coverage == SemanticCoverage.COMPLETE
    mana_fx = [
        e
        for a in altar.abilities
        if getattr(a, "effects", None)
        for e in a.effects
        if isinstance(e, AddManaEffect)
    ]
    assert mana_fx
    assert mana_fx[0].amount == ManaAmount(any_color=1)


def test_live_gravecrawler_compiles_cast_from_gy_zombie_gate():
    """Current Scryfall Gravecrawler: can't-block + cast-from-GY if Zombie."""
    report_card = _compile("Gravecrawler")
    assert report_card.coverage == SemanticCoverage.COMPLETE
    cast_abs = [
        a
        for a in report_card.abilities
        if isinstance(a, ActivatedAbility) and a.requires_zombie
    ]
    assert cast_abs
    assert cast_abs[0].costs[0].amount == ManaAmount(black=1)


def test_explore_pair_rediscovers_live_gravecrawler_plus_altar():
    altar = _compile("Phyrexian Altar")
    gc = _compile("Gravecrawler")
    pairs = InteractionIndex([altar, gc]).candidate_pairs()
    assert pairs
    assert any("sac_recursion" in p.reasons for p in pairs)

    hit = explore_pair(altar, gc) or explore_pair(gc, altar)
    assert hit is not None
    assert hit.proof.status == VerificationStatus.VERIFIED
    assert hit.witness.classification.strict_two_card is True
    assert hit.witness.classification.generic_prerequisites


def test_spellbook_shaped_recovery_on_live_gravecrawler_altar():
    variant = {
        "id": "curriculum-live-gravecrawler-altar",
        "uses": [
            {"card": {"name": "Gravecrawler"}},
            {"card": {"name": "Phyrexian Altar"}},
        ],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    cards = {
        "gravecrawler": _compile("Gravecrawler"),
        "phyrexian altar": _compile("Phyrexian Altar"),
    }
    report = evaluate_reference_subset([variant], cards_by_name=cards)
    assert report.counts.eligible == 1
    assert report.counts.rediscovered == 1


def test_explore_pair_rediscovers_activated_return_curriculum_altar_gravecrawler():
    altar = _compile("Phyrexian Altar")
    gc = _compile("GravecrawlerActivatedReturn")
    pairs = InteractionIndex([altar, gc]).candidate_pairs()
    assert pairs
    assert any("sac_recursion" in p.reasons for p in pairs)

    hit = explore_pair(altar, gc) or explore_pair(gc, altar)
    assert hit is not None
    assert hit.proof.status == VerificationStatus.VERIFIED
    assert hit.witness.classification.strict_two_card is True


def test_spellbook_shaped_recovery_on_activated_return_curriculum():
    variant = {
        "id": "curriculum-activated-gravecrawler-altar",
        "uses": [
            {"card": {"name": "Gravecrawler"}},
            {"card": {"name": "Phyrexian Altar"}},
        ],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    cards = {
        "gravecrawler": _compile("GravecrawlerActivatedReturn"),
        "phyrexian altar": _compile("Phyrexian Altar"),
    }
    report = evaluate_reference_subset([variant], cards_by_name=cards)
    assert report.counts.eligible == 1
    assert report.counts.rediscovered == 1


def test_explore_pair_rediscovers_fixture_phoenix_plus_real_altar():
    phoenix = compile_card(
        GOLD_ORACLE_FIXTURES["oracle:phoenix"].oracle_id,
        GOLD_ORACLE_FIXTURES["oracle:phoenix"].name,
        GOLD_ORACLE_FIXTURES["oracle:phoenix"].oracle_text,
        GOLD_ORACLE_FIXTURES["oracle:phoenix"].types,
    )
    altar = _compile("Phyrexian Altar")
    hit = explore_pair(altar, phoenix) or explore_pair(phoenix, altar)
    assert hit is not None
    assert hit.proof.status == VerificationStatus.VERIFIED
