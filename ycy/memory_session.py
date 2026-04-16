from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ycy import config

Role = Literal["user", "assistant", "system", "tool"]


@dataclass
class Turn:
    role: Role
    content: Any
    ts: float


@dataclass
class SessionMeta:
    session_id: str
    created_at: str
    updated_at: str
    title: str | None = None


@dataclass
class SessionFile:
    meta: SessionMeta
    history: list[Turn]


def _sessions_dir() -> Path:
    d = config.SESSIONS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def create_new_session() -> SessionFile:
    sid = _new_session_id()
    now = _now_iso()
    meta = SessionMeta(session_id=sid, created_at=now, updated_at=now)
    return SessionFile(meta=meta, history=[])


def session_path(meta: SessionMeta) -> Path:
    ts = meta.created_at.replace(":", "").replace("-", "").replace("Z", "").replace("T", "-")
    return _sessions_dir() / f"{ts}_session_{meta.session_id}.json"


def _to_jsonable(value: Any) -> Any:
    """将任意对象尽量转换为可 JSON 序列化的数据结构。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _to_jsonable(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return _to_jsonable(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_jsonable(vars(value))
        except Exception:
            pass
    return str(value)


def save_session(sess: SessionFile) -> Path:
    sess.meta.updated_at = _now_iso()
    path = session_path(sess.meta)
    payload = {
        "meta": asdict(sess.meta),
        "history": [_to_jsonable(asdict(t)) for t in sess.history],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_session(identifier: str) -> SessionFile:
    """
    identifier:
    - "latest"：最近修改的会话
    - 会话文件名（含/不含路径）
    - session_id 或其前缀
    """
    d = _sessions_dir()
    candidates = sorted(d.glob("*_session_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError("暂无已保存会话。")

    target: Path | None = None
    if identifier in ("latest", ""):
        target = candidates[-1]
    else:
        name = Path(identifier).name
        if (d / name).exists():
            target = d / name
        else:
            # 按 session_id / 前缀匹配
            for p in reversed(candidates):
                sid = p.stem.split("_session_")[-1]
                if sid.startswith(identifier):
                    target = p
                    break
    if target is None:
        raise FileNotFoundError(f"未找到匹配的会话：{identifier}")

    raw = json.loads(target.read_text(encoding="utf-8"))
    meta = SessionMeta(**raw["meta"])
    history = [Turn(**t) for t in raw.get("history", [])]
    return SessionFile(meta=meta, history=history)


def append_turn(sess: SessionFile, role: Role, content: Any) -> None:
    sess.history.append(Turn(role=role, content=content, ts=datetime.utcnow().timestamp()))

