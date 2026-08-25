"""DuckDB + JSONL persistence for M4 adjudications."""

from __future__ import annotations

import atexit
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Self

import duckdb

from mtg_loop_engine.eval.schema import (
    AdjudicationClass,
    AdjudicationFailureReason,
    AdjudicationRecord,
    CandidateRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "eval" / "adjudications.duckdb"
DEFAULT_JSONL = REPO_ROOT / "eval" / "adjudications" / "gold_pool_extras.jsonl"

_LOCK_PID_RE = re.compile(r"\(PID (\d+)\)")

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
    skipped BOOLEAN,
    failure_reasons VARCHAR
);
"""


class DuckDBLockError(RuntimeError):
    """Raised when another process already holds the adjudications DuckDB file lock."""


def lock_holder_pid(message: str) -> int | None:
    """Parse the holding PID from a DuckDB conflicting-lock message, if present."""
    match = _LOCK_PID_RE.search(message)
    return int(match.group(1)) if match else None


def _format_lock_error(db_path: Path, duckdb_msg: str) -> str:
    lines = [
        f"Could not open {db_path}: another process holds the DuckDB lock.",
        "Stop other `adjudicate-workbench` / Streamlit instances, then retry.",
        "Ctrl+C the terminal that launched the workbench (closing the browser tab is not enough).",
    ]
    pid = lock_holder_pid(duckdb_msg)
    if pid is not None:
        lines.append(f"Lock holder PID: {pid} — try: kill {pid}")
    lines.append(f"({duckdb_msg})")
    return "\n".join(lines)


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    try:
        return duckdb.connect(str(db_path))
    except duckdb.IOException as exc:
        msg = str(exc)
        if "Conflicting lock" in msg or "Could not set lock" in msg:
            raise DuckDBLockError(_format_lock_error(db_path, msg)) from exc
        raise


def assert_db_unlocked(db_path: Path | None = None) -> None:
    """Raise DuckDBLockError if another process holds the file lock."""
    path = Path(db_path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = _connect(path)
    con.close()


class AdjudicationStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = _connect(self.db_path)
        self._closed = False
        self.con.execute(_SCHEMA)
        self._migrate()
        # Process exit (incl. Streamlit SIGINT) should release the file lock.
        atexit.register(self.close)

    def _migrate(self) -> None:
        cols = {
            row[1]
            for row in self.con.execute("PRAGMA table_info('adjudications')").fetchall()
        }
        if "failure_reasons" not in cols:
            self.con.execute(
                "ALTER TABLE adjudications ADD COLUMN failure_reasons VARCHAR"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.con.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

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
             engine_version, oracle_snapshot_hash, skipped, failure_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps([r.value for r in record.failure_reasons]),
            ],
        )

    def get_adjudication(self, candidate_id: str) -> AdjudicationRecord | None:
        row = self.con.execute(
            """
            SELECT candidate_id, adjudication, notes, reviewed_at, proof_hash,
                   engine_version, oracle_snapshot_hash, skipped, failure_reasons
            FROM adjudications WHERE candidate_id = ?
            """,
            [candidate_id],
        ).fetchone()
        if row is None:
            return None
        raw_reasons = row[8]
        reasons: list[AdjudicationFailureReason] = []
        if raw_reasons:
            parsed = json.loads(raw_reasons) if isinstance(raw_reasons, str) else raw_reasons
            reasons = [AdjudicationFailureReason(r) for r in parsed]
        return AdjudicationRecord(
            candidate_id=row[0],
            adjudication=AdjudicationClass(row[1]),
            notes=row[2] or "",
            reviewed_at=row[3],
            proof_hash=row[4],
            engine_version=row[5],
            oracle_snapshot_hash=row[6],
            skipped=bool(row[7]),
            failure_reasons=reasons,
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
            # Unreviewed = no adjudication yet (skipped counts as reviewed).
            if reviewed is False and adj is not None:
                continue
            items.append((candidate, adj))
        return items

    def export_jsonl(self, path: Path, *, corpus: str | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for candidate in self.list_candidates(corpus=corpus):
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
