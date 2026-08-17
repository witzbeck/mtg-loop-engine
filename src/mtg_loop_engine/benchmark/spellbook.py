"""Commander Spellbook reference corpus extract + DuckDB store."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import httpx

from mtg_loop_engine.config import EngineConfig

SPELLBOOK_VARIANTS_URL = "https://backend.commanderspellbook.com/variants/"
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "spellbook"

# Conventional feature-name needles for "repeatable" outcomes.
REPEATABLE_NEEDLES = (
    "infinite",
    "arbitrary",
    "near-infinite",
    "loop",
)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _variant_card_count(variant: dict[str, Any]) -> int:
    uses = variant.get("uses") or variant.get("cards") or []
    return len(uses)


def _variant_template_count(variant: dict[str, Any]) -> int:
    req = variant.get("requires") or variant.get("templates") or []
    return len(req)


def _produces_repeatable(variant: dict[str, Any]) -> bool:
    produces = variant.get("produces") or variant.get("features") or []
    for feat in produces:
        if isinstance(feat, str):
            name = feat
        elif isinstance(feat, dict):
            name = str(feat.get("name") or feat.get("feature") or "")
        else:
            name = str(feat)
        lower = name.lower()
        if any(n in lower for n in REPEATABLE_NEEDLES):
            return True
    # Some payloads nest identity differently; also check textual description.
    text = json.dumps(variant.get("description", "")).lower()
    return any(n in text for n in REPEATABLE_NEEDLES)


def is_conventional_two_card(
    variant: dict[str, Any], config: EngineConfig | None = None
) -> bool:
    cfg = config or EngineConfig()
    if _variant_card_count(variant) != cfg.max_essential_cards:
        return False
    if cfg.spellbook_require_zero_templates and _variant_template_count(variant) != 0:
        return False
    if cfg.spellbook_require_repeatable_feature and not _produces_repeatable(variant):
        return False
    if cfg.prefer_distinct_oracle_ids_in_benchmarks:
        uses = variant.get("uses") or []
        names = []
        for u in uses:
            if isinstance(u, dict):
                card = u.get("card") or u
                names.append(card.get("name") or card.get("oracleId") or str(card))
            else:
                names.append(str(u))
        if len(names) != len(set(names)):
            return False
    return True


def fetch_variants_page(
    client: httpx.Client,
    url: str = SPELLBOOK_VARIANTS_URL,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resp = client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def download_spellbook_snapshot(
    data_dir: Path | None = None,
    *,
    max_pages: int = 5,
    page_size: int = 100,
    config: EngineConfig | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Pull a bounded Spellbook variants sample and store filtered two-card rows.

    Uses public HTTP API. Bounded by max_pages for M0 practicality.
    """
    root = ensure_dir(data_dir or DEFAULT_DATA_DIR)
    cfg = config or EngineConfig()
    own = client is None
    client = client or httpx.Client(
        timeout=60.0, headers={"User-Agent": "mtg-loop-engine/0.1"}
    )
    try:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap_dir = ensure_dir(root / stamp)
        raw_path = snap_dir / "variants_raw.jsonl"
        filtered: list[dict[str, Any]] = []
        raw_count = 0
        next_url: str | None = SPELLBOOK_VARIANTS_URL
        pages = 0
        with raw_path.open("w", encoding="utf-8") as raw_out:
            while next_url and pages < max_pages:
                params = {"limit": page_size} if pages == 0 else None
                payload = fetch_variants_page(client, next_url, params=params)
                results = payload.get("results") or payload.get("data") or []
                if isinstance(payload, list):
                    results = payload
                for variant in results:
                    raw_count += 1
                    raw_out.write(json.dumps(variant) + "\n")
                    if is_conventional_two_card(variant, cfg):
                        filtered.append(variant)
                next_url = payload.get("next") if isinstance(payload, dict) else None
                pages += 1

        filtered_path = snap_dir / "variants_two_card.jsonl"
        with filtered_path.open("w", encoding="utf-8") as out:
            for row in filtered:
                out.write(json.dumps(row) + "\n")

        db_path = snap_dir / "spellbook.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute(
            "CREATE TABLE two_card_variants AS SELECT * FROM read_json_auto(?)",
            [str(filtered_path)],
        )
        con.close()

        blob = filtered_path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        manifest = {
            "source": "commander_spellbook",
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "pages_fetched": pages,
            "raw_variant_count": raw_count,
            "filtered_two_card_count": len(filtered),
            "spellbook_snapshot_hash": digest,
            "filter": {
                "max_essential_cards": cfg.max_essential_cards,
                "require_zero_templates": cfg.spellbook_require_zero_templates,
                "require_repeatable_feature": cfg.spellbook_require_repeatable_feature,
                "prefer_distinct": cfg.prefer_distinct_oracle_ids_in_benchmarks,
            },
            "notes": "Reference corpus only; absence ≠ novel.",
        }
        (snap_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        latest = root / "latest"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(snap_dir.name)
        return manifest
    finally:
        if own:
            client.close()
