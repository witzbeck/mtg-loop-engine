"""Unit tests for Spellbook filter helpers."""

from mtg_loop_engine.benchmark.spellbook import is_conventional_two_card
from mtg_loop_engine.config import EngineConfig


def test_conventional_two_card_filter():
    variant = {
        "uses": [{"card": {"name": "A"}}, {"card": {"name": "B"}}],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    assert is_conventional_two_card(variant, EngineConfig())


def test_rejects_templates():
    variant = {
        "uses": [{"card": {"name": "A"}}, {"card": {"name": "B"}}],
        "requires": [{"template": "creature"}],
        "produces": [{"name": "Infinite mana"}],
    }
    assert not is_conventional_two_card(variant, EngineConfig())


def test_rejects_three_cards():
    variant = {
        "uses": [
            {"card": {"name": "A"}},
            {"card": {"name": "B"}},
            {"card": {"name": "C"}},
        ],
        "requires": [],
        "produces": [{"name": "Infinite mana"}],
    }
    assert not is_conventional_two_card(variant, EngineConfig())
