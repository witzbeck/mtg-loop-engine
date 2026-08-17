"""Scryfall ingest helpers (offline unit checks)."""

import json
from pathlib import Path

from mtg_loop_engine.cards.ingest import sha256_file


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    digest = sha256_file(p)
    assert len(digest) == 64


def test_manifest_schema_roundtrip(tmp_path: Path):
    manifest = {
        "source": "scryfall",
        "oracle_snapshot_hash": "abc",
        "notes": "Local cache only.",
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["source"] == "scryfall"
