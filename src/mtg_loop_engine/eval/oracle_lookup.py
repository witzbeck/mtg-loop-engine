"""Resolve Oracle text for Spellbook names via Scryfall collection lookup."""

from __future__ import annotations

import time
from typing import Any

import httpx

from mtg_loop_engine.eval.spellbook_eval import compile_card, variant_card_names
from mtg_loop_engine.semantics.ir import CardSemantics

SCRYFALL_COLLECTION = "https://api.scryfall.com/cards/collection"


def types_from_line(type_line: str | None) -> list[str]:
    if not type_line:
        return []
    left = type_line.split("—")[0]
    return [t.strip() for t in left.replace("—", " ").split() if t.strip()]


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def fetch_named_semantics(
    names: list[str],
    *,
    client: httpx.Client | None = None,
    pause_s: float = 0.15,
) -> dict[str, CardSemantics]:
    """Deterministic compile of Scryfall Oracle text. Fail-closed on unmatched fragments."""
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    own = client is None
    client = client or httpx.Client(
        timeout=60.0, headers={"User-Agent": "mtg-loop-engine/0.1"}
    )
    out: dict[str, CardSemantics] = {}
    try:
        for batch in _chunks(unique, 75):
            payload = {"identifiers": [{"name": name} for name in batch]}
            resp = client.post(SCRYFALL_COLLECTION, json=payload)
            if resp.status_code == 429:
                time.sleep(1.0)
                resp = client.post(SCRYFALL_COLLECTION, json=payload)
            resp.raise_for_status()
            body = resp.json()
            for card in body.get("data") or []:
                name = str(card.get("name") or "")
                oracle_id = str(card.get("oracle_id") or card.get("id") or name)
                text = card.get("oracle_text") or ""
                types = types_from_line(card.get("type_line"))
                compiled = compile_card(oracle_id, name, text, types)
                out[name.casefold()] = compiled
            time.sleep(pause_s)
    finally:
        if own:
            client.close()
    return out


def names_from_variants(variants: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for variant in variants:
        for name in variant_card_names(variant):
            if name not in seen:
                seen.append(name)
    return seen
