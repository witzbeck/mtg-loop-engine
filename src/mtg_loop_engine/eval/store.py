"""DuckDB + JSONL persistence for M4 adjudications."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from mtg_loop_engine.eval.schema import (
    AdjudicationClass,
    AdjudicationRecord,
    CandidateRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "eval" / "adjudications.duckdb"
DEFAULT_JSONL = REPO_ROOT / "eval" / "adjudications" / "gold_pool_extras.jsonl"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id VARCHAR PRIMARY KEY,
    corpus VARCHAR,
    left_id VARCHAR,
    right_id VARCHAR,
    left_name VARCHAR,
    right_name VARCHAR,
    payload VARCHAR,
    proof_hash VARCHAR,
    engine_version VARCHAR,
    created_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS adjudications (
    candidate_id VARCHAR PRIMARY KEY,
    adjudication VARCHAR,
    notes VARCHAR,
    reviewed_at TIMESTAMP,
    proof_hash VARCHAR,
    engine_version VARCHAR,
    oracle_snapshot_hash VARCHAR,
    skipped BOOLEAN
);
"""


class AdjudicationStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.db_path))
        self.con.execute(_SCHEMA)

    def close(self) -> None:
        self.con.close()

    def upsert_candidate(self, record: CandidateRecord) -> None:
        payload = record.model_dump(mode="json")
        self.con.execute(
            """
            INSERT OR REPLACE INTO candidates
            (candidate_id, corpus, left_id, right_id, left_name, right_name,
             payload, proof_hash, engine_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.candidate_id,
                record.corpus,
                record.left_id,
                record.right_id,
                record.left_name,
                record.right_name,
                json.dumps(payload),
                record.proof.proof_hash,
                record.engine_version,
                datetime.now(timezone.utc),
            ],
        )

    def get_candidate(self, candidate_id: str) -> CandidateRecord | None:
        row = self.con.execute(
            "SELECT payload FROM candidates WHERE candidate_id = ?",
            [candidate_id],
        ).fetchone()
        if row is None:
            return None
        return CandidateRecord.model_validate_json(row[0])

    def list_candidates(self, *, corpus: str | None = None) -> list[CandidateRecord]:
        sql = "SELECT payload FROM candidates"
        args: list = []
        if corpus:
            sql += " WHERE corpus = ?"
            args.append(corpus)
        sql += " ORDER BY left_name, right_name"
        rows = self.con.execute(sql, args).fetchall()
        return [CandidateRecord.model_validate_json(r[0]) for r in rows]

    def save_adjudication(self, record: AdjudicationRecord) -> None:
        self.con.execute(
            """
            INSERT OR REPLACE INTO adjudications
            (candidate_id, adjudication, notes, reviewed_at, proof_hash,
             engine_version, oracle_snapshot_hash, skipped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.candidate_id,
                record.adjudication.value,
                record.notes,
                record.reviewed_at,
                record.proof_hash,
                record.engine_version,
                record.oracle_snapshot_hash,
                record.skipped,
            ],
        )

    def get_adjudication(self, candidate_id: str) -> AdjudicationRecord | None:
        row = self.con.execute(
            """
            SELECT candidate_id, adjudication, notes, reviewed_at, proof_hash,
                   engine_version, oracle_snapshot_hash, skipped
            FROM adjudications WHERE candidate_id = ?
            """,
            [candidate_id],
        ).fetchone()
        if row is None:
            return None
        return AdjudicationRecord(
            candidate_id=row[0],
            adjudication=AdjudicationClass(row[1]),
            notes=row[2] or "",
            reviewed_at=row[3],
            proof_hash=row[4],
            engine_version=row[5],
            oracle_snapshot_hash=row[6],
            skipped=bool(row[7]),
        )

    def queue(
        self,
        *,
        corpus: str | None = None,
        reviewed: bool | None = None,
    ) -> list[tuple[CandidateRecord, AdjudicationRecord | None]]:
        items: list[tuple[CandidateRecord, AdjudicationRecord | None]] = []
        for candidate in self.list_candidates(corpus=corpus):
            adj = self.get_adjudication(candidate.candidate_id)
            if reviewed is True and adj is None:
                continue
            if reviewed is False and adj is not None and not adj.skipped:
                continue
            items.append((candidate, adj))
        return items

    def export_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for candidate in self.list_candidates():
            adj = self.get_adjudication(candidate.candidate_id)
            rows.append(
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "adjudication": adj.model_dump(mode="json") if adj else None,
                }
            )
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, default=str) + "\n")

    def import_jsonl(self, path: Path) -> int:
        count = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                blob = json.loads(line)
                candidate = CandidateRecord.model_validate(blob["candidate"])
                self.upsert_candidate(candidate)
                if blob.get("adjudication"):
                    self.save_adjudication(
                        AdjudicationRecord.model_validate(blob["adjudication"])
                    )
                count += 1
        return count
