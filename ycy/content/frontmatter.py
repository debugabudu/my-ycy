"""共享的 YAML 风格 frontmatter 拆分与元数据行解析（SKILL / AGENT 等）。"""

import re
from typing import Any


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """
    从 Markdown 文本中拆出第一个 --- 块。
    返回 (frontmatter_raw, body)；若无合法块则 (None, 原文本去首尾空白)。
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return None, text.strip()
    return match.group(1), match.group(2).strip()


def parse_simple_meta_lines(raw: str) -> dict[str, Any]:
    """key: value 单行元数据；不含 tools 列表等特殊规则。"""
    meta: dict[str, Any] = {}
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta


def parse_agent_meta_lines(raw: str) -> dict[str, Any]:
    """AGENT.md 元数据：支持 tools 逗号列表、max_turns、布尔。"""
    meta: dict[str, Any] = {}
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        val = v.strip()
        if key == "tools":
            if not val:
                meta[key] = []
            else:
                meta[key] = [p.strip() for p in val.split(",") if p.strip()]
        elif key == "max_turns":
            try:
                meta[key] = int(val)
            except ValueError:
                meta[key] = None
        elif key in ("use_body_as_system", "auto_claim_tasks"):
            meta[key] = val.lower() in ("true", "1", "yes")
        else:
            meta[key] = val
    return meta
