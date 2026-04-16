from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ycy.memory_session import load_session


def _normalize_id(name: str) -> str:
    return "".join(ch for ch in name.strip().lower().replace(" ", "-") if ch.isalnum() or ch in "-_")


def draft_skill_from_latest_session(
    *,
    skills_dir: Path,
    name: str,
    focus: str = "",
    n_rounds: int = 6,
    overwrite: bool = False,
) -> Path:
    sid = _normalize_id(name)
    if not sid:
        raise ValueError("name 不能为空")
    sess = load_session("latest")
    turns = sess.history[-max(2, n_rounds * 2) :]
    user_points = [str(t.content).strip() for t in turns if t.role == "user" and str(t.content).strip()]
    assistant_points = [str(t.content).strip() for t in turns if t.role == "assistant" and str(t.content).strip()]
    summary = (focus or (user_points[-1] if user_points else "从最近对话沉淀的技能")).replace("\n", " ")[:80]
    today = datetime.utcnow().strftime("%Y-%m-%d")

    lines = [
        "---",
        f"name: {sid}",
        f"description: {summary}",
        f"summary: {summary}",
        "version: 0.1.0",
        f"updated: {today}",
        "tags: draft,chat",
        "---",
        "",
        f"# {sid}",
        "",
        "## 适用场景",
        f"- {summary}",
        "",
        "## 关键输入",
    ]
    if user_points:
        for p in user_points[-5:]:
            lines.append(f"- {p[:200]}")
    else:
        lines.append("- （从对话中提取）")
    lines.extend(
        [
            "",
            "## 建议步骤",
            "1. 复述目标与约束。",
            "2. 拆解执行步骤并标注检查点。",
            "3. 输出结构化结果与下一步建议。",
            "",
            "## 输出格式",
            "- 结论",
            "- 关键步骤",
            "- 风险与后续",
            "",
            "## 对话提炼（assistant）",
        ]
    )
    if assistant_points:
        for p in assistant_points[-5:]:
            lines.append(f"- {p[:200]}")
    else:
        lines.append("- （暂无可提炼内容）")

    target = skills_dir / sid / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Skill 已存在：{target}（可传 overwrite=true）")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target

