import os
from datetime import datetime
from pathlib import Path

from ycy.config import WORKDIR


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越出工作区：{p}")
    return path


def _backup_mode() -> str:
    mode = os.getenv("YCY_FILE_BACKUP_MODE", "bak").strip().lower()
    return mode if mode in {"none", "bak", "trash"} else "bak"


def _backup_file(fp: Path) -> Path | None:
    if not fp.exists():
        return None
    mode = _backup_mode()
    if mode == "none":
        return None
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if mode == "bak":
        backup = fp.with_name(f"{fp.name}.bak.{ts}")
    else:
        rel = fp.relative_to(WORKDIR)
        backup = WORKDIR / ".ycy" / "trash" / f"{rel.as_posix()}.{ts}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(fp.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return backup


def run_read(path: str, limit: int | None = None) -> str:
    try:
        full = safe_path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        if limit and limit < len(full):
            lines = full[:limit] + [f"...（另有 {len(full) - limit} 行未显示）"]
        else:
            lines = full
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"错误：{e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        backup = _backup_file(fp)
        fp.write_text(content, encoding="utf-8")
        suffix = f"，备份：{backup}" if backup else ""
        return f"已写入 {path}（{len(content)} 字节）{suffix}"
    except Exception as e:
        return f"错误：{e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text(encoding="utf-8", errors="replace")
        if old_text not in c:
            return f"错误：在 {path} 中未找到待替换文本"
        backup = _backup_file(fp)
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
        suffix = f"，备份：{backup}" if backup else ""
        return f"已编辑 {path}{suffix}"
    except Exception as e:
        return f"错误：{e}"


def run_restore_backup(path: str, backup_path: str) -> str:
    try:
        fp = safe_path(path)
        bp = safe_path(backup_path)
        if not bp.exists():
            return f"错误：备份文件不存在 {backup_path}"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(bp.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        return f"已从备份恢复 {path} <- {backup_path}"
    except Exception as e:
        return f"错误：{e}"
