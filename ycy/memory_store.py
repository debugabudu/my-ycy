from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class MemoryEntry:
    id: str
    created_at: str
    updated_at: str
    source: str
    run_id: str | None
    text: str
    summary: str | None
    tags: list[str]
    anchors: list[str]
    importance: int


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    run_id TEXT,
                    text TEXT NOT NULL,
                    summary TEXT,
                    tags_json TEXT NOT NULL,
                    anchors_json TEXT NOT NULL,
                    importance INTEGER NOT NULL DEFAULT 3,
                    deleted INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def append(
        self,
        *,
        text: str,
        source: str = "user_note",
        run_id: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        anchors: list[str] | None = None,
        importance: int = 3,
    ) -> MemoryEntry:
        now = _now_iso()
        mid = uuid.uuid4().hex[:16]
        tags = tags or []
        anchors = anchors or []
        importance = max(1, min(5, int(importance)))
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO memories (
                    id, created_at, updated_at, source, run_id, text, summary,
                    tags_json, anchors_json, importance, deleted
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    mid,
                    now,
                    now,
                    source,
                    run_id,
                    text,
                    summary,
                    json.dumps(tags, ensure_ascii=False),
                    json.dumps(anchors, ensure_ascii=False),
                    importance,
                ),
            )
        return MemoryEntry(
            id=mid,
            created_at=now,
            updated_at=now,
            source=source,
            run_id=run_id,
            text=text,
            summary=summary,
            tags=tags,
            anchors=anchors,
            importance=importance,
        )

    def search(
        self,
        *,
        query: str = "",
        tags: list[str] | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        tags = tags or []
        limit = max(1, min(100, int(limit)))
        sql = [
            "SELECT * FROM memories WHERE deleted = 0",
        ]
        params: list[Any] = []
        if query.strip():
            sql.append("AND (text LIKE ? OR IFNULL(summary, '') LIKE ?)")
            q = f"%{query.strip()}%"
            params.extend([q, q])
        if from_time:
            sql.append("AND created_at >= ?")
            params.append(from_time)
        if to_time:
            sql.append("AND created_at <= ?")
            params.append(to_time)
        sql.append("ORDER BY created_at DESC")
        sql.append("LIMIT ?")
        params.append(limit * 3 if tags else limit)
        with self._conn() as c:
            rows = c.execute(" ".join(sql), params).fetchall()
        out = [self._row_to_entry(r) for r in rows]
        if tags:
            tset = set(tags)
            out = [m for m in out if tset.issubset(set(m.tags))]
        return out[:limit]

    def compact(self, *, max_entries: int = 500, preserve_anchors: bool = True) -> dict[str, Any]:
        """压缩策略：当条目过多时，删除最旧的低重要级条目；含 anchors 的条目受保护。"""
        max_entries = max(20, int(max_entries))
        with self._conn() as c:
            total = int(
                c.execute("SELECT COUNT(1) FROM memories WHERE deleted=0").fetchone()[0]
            )
            if total <= max_entries:
                return {"total": total, "deleted": 0, "kept": total}
            need_delete = total - max_entries
            rows = c.execute(
                "SELECT id, anchors_json FROM memories WHERE deleted=0 ORDER BY created_at ASC"
            ).fetchall()
            candidates: list[str] = []
            for r in rows:
                anchors = json.loads(r["anchors_json"] or "[]")
                if preserve_anchors and anchors:
                    continue
                candidates.append(r["id"])
                if len(candidates) >= need_delete:
                    break
            deleted = 0
            if candidates:
                c.executemany(
                    "UPDATE memories SET deleted=1, updated_at=? WHERE id=?",
                    [(_now_iso(), cid) for cid in candidates],
                )
                deleted = len(candidates)
            kept = total - deleted
            return {"total": total, "deleted": deleted, "kept": kept}

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=row["source"],
            run_id=row["run_id"],
            text=row["text"],
            summary=row["summary"],
            tags=json.loads(row["tags_json"] or "[]"),
            anchors=json.loads(row["anchors_json"] or "[]"),
            importance=int(row["importance"]),
        )

