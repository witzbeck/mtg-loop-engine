"""Scryfall Oracle text helpers (DFC face join)."""

from mtg_loop_engine.eval.oracle_lookup import oracle_text_from_card


def test_oracle_text_from_card_joins_dfc_faces_when_top_level_empty():
    card = {
        "name": "Sorin // Something",
        "oracle_text": "",
        "card_faces": [
            {"oracle_text": "Front ability text."},
            {"oracle_text": "Back ability text."},
        ],
    }
    assert oracle_text_from_card(card) == "Front ability text.\n\nBack ability text."


def test_oracle_text_from_card_prefers_top_level():
    card = {
        "oracle_text": "Top level.",
        "card_faces": [{"oracle_text": "Ignored."}],
    }
    assert oracle_text_from_card(card) == "Top level."
