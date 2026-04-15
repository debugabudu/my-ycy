"""启动策略：控制是否在启动前清空持久化运行状态。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger("ycy.startup")


def _clear_tasks(tasks_dir: Path) -> int:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    removed = 0
    for fp in tasks_dir.glob("task_*.json"):
        fp.unlink(missing_ok=True)
        removed += 1
    return removed


def _reset_team(team_dir: Path, inbox_dir: Path) -> int:
    team_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    cleared_inboxes = 0
    for fp in inbox_dir.glob("*.jsonl"):
        fp.write_text("", encoding="utf-8")
        cleared_inboxes += 1

    cfg = team_dir / "config.json"
    cfg.write_text(
        json.dumps(
            {"team_name": "default", "members": []},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return cleared_inboxes


def apply_startup_policy(
    policy: str,
    *,
    tasks_dir: Path,
    team_dir: Path,
    inbox_dir: Path,
) -> None:
    """应用启动策略。

    - fresh: 清空任务文件、清空收件箱、重置 team 配置
    - resume: 保留历史状态
    """
    if policy == "resume":
        _log.info("Startup policy=resume, keep existing runtime state")
        return
    if policy != "fresh":
        _log.warning("Unknown startup policy=%s, fallback to resume", policy)
        return

    removed_tasks = _clear_tasks(tasks_dir)
    cleared_inboxes = _reset_team(team_dir, inbox_dir)
    _log.info(
        "Startup policy=fresh, removed_tasks=%d cleared_inboxes=%d",
        removed_tasks,
        cleared_inboxes,
    )
