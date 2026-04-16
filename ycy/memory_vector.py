from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text)]


def _embed(text: str, dim: int = 128) -> list[float]:
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for t in tokens:
        idx = hash(t) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return vec
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


class VectorStore:
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
                CREATE TABLE IF NOT EXISTS vector_items (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    ref_type TEXT NOT NULL,
                    ref_id TEXT,
                    text TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    meta_json TEXT NOT NULL
                )
                """
            )

    def upsert_text(
        self,
        *,
        namespace: str,
        text: str,
        ref_type: str = "memory",
        ref_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> str:
        rid = ref_id or uuid.uuid4().hex[:16]
        vec = _embed(text)
        meta = meta or {}
        item_id = f"{namespace}:{ref_type}:{rid}"
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO vector_items (id, namespace, ref_type, ref_id, text, vector_json, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text=excluded.text,
                    vector_json=excluded.vector_json,
                    meta_json=excluded.meta_json
                """,
                (
                    item_id,
                    namespace,
                    ref_type,
                    rid,
                    text,
                    json.dumps(vec, ensure_ascii=False),
                    json.dumps(meta, ensure_ascii=False),
                ),
            )
        return item_id

    def index_directory(
        self,
        *,
        namespace: str,
        directory: Path,
        suffixes: tuple[str, ...] = (".md", ".txt"),
        chunk_size: int = 800,
    ) -> dict[str, Any]:
        if not directory.exists() or not directory.is_dir():
            raise FileNotFoundError(f"目录不存在：{directory}")
        files = [
            p
            for p in directory.rglob("*")
            if p.is_file() and (not suffixes or p.suffix.lower() in suffixes)
        ]
        total_chunks = 0
        for p in files:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for i in range(0, len(txt), max(100, chunk_size)):
                chunk = txt[i : i + chunk_size].strip()
                if not chunk:
                    continue
                self.upsert_text(
                    namespace=namespace,
                    text=chunk,
                    ref_type="file_chunk",
                    ref_id=f"{p}:{i}",
                    meta={"path": str(p), "offset": i},
                )
                total_chunks += 1
        return {"namespace": namespace, "files": len(files), "chunks": total_chunks}

    def search(
        self, *, namespace: str, query: str, top_k: int = 5, min_score: float = 0.05
    ) -> list[dict[str, Any]]:
        qv = _embed(query)
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM vector_items WHERE namespace=?",
                (namespace,),
            ).fetchall()
        scored = []
        for r in rows:
            vec = json.loads(r["vector_json"])
            score = _cosine(qv, vec)
            if score >= min_score:
                scored.append(
                    {
                        "id": r["id"],
                        "ref_type": r["ref_type"],
                        "ref_id": r["ref_id"],
                        "text": r["text"],
                        "meta": json.loads(r["meta_json"] or "{}"),
                        "score": round(score, 4),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: max(1, min(20, int(top_k)))]

