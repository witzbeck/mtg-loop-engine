"""Scryfall Oracle Cards bulk snapshot ingest."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SCRYFALL_BULK_API = "https://api.scryfall.com/bulk-data"
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "scryfall"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_oracle_bulk_info(client: httpx.Client | None = None) -> dict[str, Any]:
    own = client is None
    client = client or httpx.Client(timeout=60.0, headers={"User-Agent": "mtg-loop-engine/0.1"})
    try:
        resp = client.get(SCRYFALL_BULK_API)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("data", []):
            if item.get("type") == "oracle_cards":
                return item
        raise RuntimeError("oracle_cards bulk item not found")
    finally:
        if own:
            client.close()


def download_oracle_snapshot(
    data_dir: Path | None = None,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Download Oracle Cards bulk JSONL.gz into a versioned local snapshot.

    Does not commit card data; callers must keep `data/` gitignored.
    """
    root = ensure_dir(data_dir or DEFAULT_DATA_DIR)
    own = client is None
    client = client or httpx.Client(timeout=120.0, headers={"User-Agent": "mtg-loop-engine/0.1"})
    try:
        info = fetch_oracle_bulk_info(client)
        download_uri = info.get("download_uri") or info.get("jsonl_download_uri")
        if not download_uri:
            raise RuntimeError("no download URI for oracle_cards")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap_dir = ensure_dir(root / stamp)
        archive_path = snap_dir / "oracle_cards.jsonl.gz"
        with client.stream("GET", download_uri) as resp:
            resp.raise_for_status()
            with archive_path.open("wb") as out:
                for chunk in resp.iter_bytes():
                    out.write(chunk)
        digest = sha256_file(archive_path)
        manifest = {
            "source": "scryfall",
            "bulk_type": "oracle_cards",
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "download_uri": download_uri,
            "updated_at": info.get("updated_at"),
            "archive": str(archive_path.name),
            "oracle_snapshot_hash": digest,
            "scryfall_id": info.get("id"),
            "notes": (
                "Local cache only. Do not redistribute Oracle bulk JSON in git. "
                "See Scryfall API terms."
            ),
        }
        manifest_path = snap_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        latest = root / "latest"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(snap_dir.name)
        return manifest
    finally:
        if own:
            client.close()


def load_oracle_cards(snapshot_dir: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    archive = snapshot_dir / "oracle_cards.jsonl.gz"
    cards: list[dict[str, Any]] = []
    with gzip.open(archive, "rt", encoding="utf-8") as f:
        for line in f:
            cards.append(json.loads(line))
            if limit is not None and len(cards) >= limit:
                break
    return cards


def read_manifest(snapshot_dir: Path) -> dict[str, Any]:
    return json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
