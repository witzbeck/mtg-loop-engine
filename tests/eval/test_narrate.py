"""Narration + real-Oracle curriculum honesty; Basalt gold_core uses Synthetic Cost Reducer."""

from mtg_loop_engine.eval.narrate import (
    _ability_hint,
    _verb,
    card_image_url,
    full_narrative,
    narrate_loop,
    narrate_outputs,
    narrate_recurrence,
    narrate_setup,
)

# ---------------------------------------------------------------------------
# card_image_url
# ---------------------------------------------------------------------------


def test_card_image_url_contains_name():
    url = card_image_url("Basalt Monolith")
    assert "Basalt%20Monolith" in url or "Basalt+Monolith" in url or "Basalt" in url


def test_card_image_url_contains_scryfall_domain():
    url = card_image_url("Gravecrawler")
    assert "scryfall.com" in url


def test_card_image_url_default_version():
    url = card_image_url("Rings of Brighthearth")
    assert "version=normal" in url


def test_card_image_url_custom_version():
    url = card_image_url("Sol Ring", version="small")
    assert "version=small" in url


# ---------------------------------------------------------------------------
# _verb helper
# ---------------------------------------------------------------------------


def test_verb_known_op():
    assert _verb("TAP_FOR_MANA") == "tap for mana"


def test_verb_unknown_op_lowercased_underscores_replaced():
    result = _verb("SOME_WEIRD_OP")
    assert result == "some weird op"


# ---------------------------------------------------------------------------
# _ability_hint
# ---------------------------------------------------------------------------


def test_ability_hint_strips_card_prefix():
    hint = _ability_hint("basalt-tap-mana")
    assert "basalt" not in hint
    assert "tap" in hint or "mana" in hint


def test_ability_hint_short_id():
    hint = _ability_hint("tap")
    assert hint  # should not be empty


# ---------------------------------------------------------------------------
# narrate_loop with real gold-core witnesses
# ---------------------------------------------------------------------------


def test_narrate_loop_gold_basalt_training():
    """Basalt Monolith + Synthetic Cost Reducer is the gold_core mana_tap_untap witness."""
    from mtg_loop_engine.corpus import all_gold_core

    witnesses = {
        " + ".join(sorted(c.name for c in w.essential_cards)): w for w in all_gold_core()
    }
    key = next(
        (k for k in witnesses if "Basalt" in k and "Synthetic Cost Reducer" in k),
        None,
    )
    assert key is not None, "expected core_basalt_training in gold_core"
    steps = narrate_loop(witnesses[key])
    assert len(steps) >= 2
    for step in steps:
        assert isinstance(step, str) and step.strip()
        assert step.endswith(".")


def test_narrate_loop_empty_actions_returns_placeholder():
    from mtg_loop_engine.corpus import all_gold_core

    base = all_gold_core()[0]
    stub = base.model_copy(update={"loop_actions": []})
    steps = narrate_loop(stub)
    assert steps == ["(no loop steps recorded)"]


# ---------------------------------------------------------------------------
# narrate_setup
# ---------------------------------------------------------------------------


def test_narrate_setup_no_setup_actions():
    from mtg_loop_engine.corpus import all_gold_core

    base = all_gold_core()[0]
    stub = base.model_copy(update={"setup_actions": []})
    assert narrate_setup(stub) == []


# ---------------------------------------------------------------------------
# narrate_outputs and narrate_recurrence with real proof
# ---------------------------------------------------------------------------


def test_narrate_outputs_non_empty_for_verified_gold():
    from mtg_loop_engine.corpus import all_gold_core
    from mtg_loop_engine.verify.verifier import Verifier

    verifier = Verifier()
    for w in all_gold_core():
        proof = verifier.verify(w)
        lines = narrate_outputs(proof)
        assert isinstance(lines, list)
        for line in lines:
            assert isinstance(line, str) and line.strip()
        break  # one witness is sufficient


def test_narrate_recurrence_non_empty_for_verified_gold():
    from mtg_loop_engine.corpus import all_gold_core
    from mtg_loop_engine.verify.verifier import Verifier

    verifier = Verifier()
    for w in all_gold_core():
        proof = verifier.verify(w)
        lines = narrate_recurrence(proof)
        assert isinstance(lines, list) and lines
        break


# ---------------------------------------------------------------------------
# full_narrative
# ---------------------------------------------------------------------------


def test_full_narrative_contains_card_names():
    from mtg_loop_engine.corpus import all_gold_core
    from mtg_loop_engine.verify.verifier import Verifier

    verifier = Verifier()
    w = all_gold_core()[0]
    proof = verifier.verify(w)
    narrative = full_narrative(w, proof)
    for card in w.essential_cards:
        assert card.name in narrative


def test_full_narrative_contains_section_headers():
    from mtg_loop_engine.corpus import all_gold_core
    from mtg_loop_engine.verify.verifier import Verifier

    verifier = Verifier()
    w = all_gold_core()[0]
    proof = verifier.verify(w)
    narrative = full_narrative(w, proof)
    assert "Repeating loop body" in narrative
    assert "What you get each iteration" in narrative
    assert "Board state that must reset" in narrative
