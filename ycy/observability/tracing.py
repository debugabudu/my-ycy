"""JSONL 调用轨迹：run_id、span 层级、LLM 与工具审计（P0）。"""

from __future__ import annotations

from datetime import datetime
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_log = logging.getLogger("ycy.trace")

_emitted: threading.local = threading.local()


def record_emitted_span(span_id: str) -> None:
    _emitted.id = span_id


def get_last_emitted_span_id() -> str | None:
    return getattr(_emitted, "id", None)


class TraceSession:
    """单次进程/REPL 会话：一个 run_id，一个 JSONL 文件。"""

    def __init__(self, run_id: str, log_path: Path):
        self.run_id = run_id
        self.log_path = log_path
        self._lock = threading.Lock()

    def write(self, record: dict[str, Any]) -> None:
        record.setdefault("ts", time.time())
        record.setdefault("run_id", self.run_id)
        line = json.dumps(record, default=str, ensure_ascii=False)
        with self._lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    @staticmethod
    def git_head() -> str | None:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=3,
            )
            return r.stdout.strip() if r.returncode == 0 else None
        except OSError:
            return None


_SESSION: TraceSession | None = None


def is_enabled() -> bool:
    return os.getenv("YCY_TRACE", "1").lower() not in ("0", "false", "no")


def init_session(trace_dir: Path) -> TraceSession | None:
    global _SESSION
    if not is_enabled():
        _SESSION = None
        return None
    run_id = uuid.uuid4().hex[:16]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = trace_dir / f"{ts}_run_{run_id}.jsonl"
    _SESSION = TraceSession(run_id, path)
    snap = config_snapshot()
    _SESSION.write(
        {
            "event": "session.start",
            "run_id": run_id,
            "git_head": TraceSession.git_head(),
            **snap,
        }
    )
    _log.info("Trace session started run_id=%s log=%s", run_id, path)
    return _SESSION


def get_session() -> TraceSession | None:
    return _SESSION


def config_snapshot() -> dict[str, Any]:
    from ycy import config as cfg

    return {
        "model_id": cfg.MODEL,
        "workdir": str(cfg.WORKDIR),
        "agents_dir": str(cfg.AGENTS_DIR),
        "skills_dir": str(cfg.SKILLS_DIR),
    }


def log_llm_request(
    *,
    span_id: str,
    parent_span_id: str | None,
    role: str,
    model: str,
    num_messages: int,
    num_tools: int,
    max_tokens: int,
) -> None:
    s = get_session()
    if not s:
        return
    s.write(
        {
            "event": "llm.request",
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "role": role,
            "model": model,
            "num_messages": num_messages,
            "num_tools": num_tools,
            "max_tokens": max_tokens,
        }
    )


def log_llm_response(
    *,
    span_id: str,
    role: str,
    stop_reason: str | None,
    tool_use_names: list[str],
    duration_ms: float | None = None,
) -> None:
    s = get_session()
    if not s:
        return
    row: dict[str, Any] = {
        "event": "llm.response",
        "span_id": span_id,
        "role": role,
        "stop_reason": stop_reason,
        "tool_use_names": tool_use_names,
    }
    if duration_ms is not None:
        row["duration_ms"] = round(duration_ms, 2)
    s.write(row)


def log_tool_execute(
    *,
    span_id: str,
    role: str,
    tool_name: str,
    input_preview: str,
    output_preview: str,
    duration_ms: float,
    error: str | None,
) -> None:
    s = get_session()
    if not s:
        return
    s.write(
        {
            "event": "tool.execute",
            "llm_span_id": span_id,
            "role": role,
            "tool_name": tool_name,
            "input_preview": input_preview[:2000],
            "output_preview": output_preview[:2000],
            "duration_ms": round(duration_ms, 2),
            "error": error,
        }
    )
