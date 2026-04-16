from __future__ import annotations

from datetime import datetime
from pathlib import Path


def build_skill_template(skill_id: str, *, title: str | None = None, description: str = "") -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    display = title or skill_id
    desc = description or f"{display} 的流程化操作说明。"
    return f"""---
name: {skill_id}
description: {desc}
summary: {desc}
version: 0.1.0
updated: {today}
tags: general
---

# {display}

## 适用场景
- 适用于需要标准化执行的场景。

## 输入检查清单
- 目标是否明确
- 约束是否明确（时间、范围、格式）
- 是否需要外部工具支持

## 标准步骤
1. 明确目标与上下文。
2. 生成可执行步骤。
3. 输出结果并附带检查项。

## 输出格式
- 结论
- 关键步骤
- 风险与后续建议

## 失败回退策略
- 信息不足时先列缺失项并请求补充。
- 工具失败时给出替代路径。

## 示例
- 输入：帮我整理会议纪要
- 输出：按议题、结论、待办、责任人结构化给出
"""


def init_skill_file(skills_dir: Path, skill_id: str, *, title: str | None = None, description: str = "") -> Path:
    target_dir = skills_dir / skill_id
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "SKILL.md"
    if path.exists():
        raise FileExistsError(f"Skill 已存在：{path}")
    path.write_text(
        build_skill_template(skill_id, title=title, description=description),
        encoding="utf-8",
    )
    return path

