from pathlib import Path

from ycy.config import WORKDIR


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越出工作区：{p}")
    return path


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
        fp.write_text(content, encoding="utf-8")
        return f"已写入 {path}（{len(content)} 字节）"
    except Exception as e:
        return f"错误：{e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text(encoding="utf-8", errors="replace")
        if old_text not in c:
            return f"错误：在 {path} 中未找到待替换文本"
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
        return f"已编辑 {path}"
    except Exception as e:
        return f"错误：{e}"
