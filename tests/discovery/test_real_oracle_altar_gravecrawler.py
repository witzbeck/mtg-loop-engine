"""Real-Oracle Phyrexian Altar + Gravecrawler: compile → join → explore rediscovery."""

from mtg_loop_engine.eval.spellbook_eval import compile_card, evaluate_reference_subset
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import AddManaEffect, ManaAmount
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(name: str):
    row = REAL_ORACLE_CURRICULUM[name]
    return compile_card(
        f"oracle:{name.lower().replace(' ', '-')}",
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


def test_explore_pair_rediscovers_real_altar_gravecrawler():
    altar = _compile("Phyrexian Altar")
    gc = _compile("Gravecrawler")
    pairs = InteractionIndex([altar, gc]).candidate_pairs()
    assert pairs
    assert any("sac_recursion" in p.reasons for p in pairs)

    hit = explore_pair(altar, gc) or explore_pair(gc, altar)
    assert hit is not None
    assert hit.proof.status == VerificationStatus.VERIFIED
    assert hit.witness.classification.strict_two_card is True


def test_spellbook_shaped_recovery_rediscovers_altar_gravecrawler():
    variant = {
        "id": "spellbook-shaped-gravecrawler-altar",
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
    assert report.rows[0].stage.value == "recovered"
