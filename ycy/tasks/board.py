import json
import threading

from ycy.config import TASKS_DIR


class TaskManager:
    def __init__(self):
        TASKS_DIR.mkdir(exist_ok=True)
        self._claim_lock = threading.Lock()

    def _next_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in TASKS_DIR.glob("task_*.json")]
        return max(ids, default=0) + 1

    def _load(self, tid: int) -> dict:
        p = TASKS_DIR / f"task_{tid}.json"
        if not p.exists():
            raise ValueError(f"未找到任务 #{tid}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, task: dict):
        (TASKS_DIR / f"task_{task['id']}.json").write_text(
            json.dumps(task, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id(),
            "subject": subject,
            "description": description,
            "status": "pending",
            "owner": None,
            "blockedBy": [],
            "blocks": [],
        }
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def get(self, tid: int) -> str:
        return json.dumps(self._load(tid), indent=2, ensure_ascii=False)

    def update(
        self,
        tid: int,
        status: str | None = None,
        add_blocked_by: list | None = None,
        add_blocks: list | None = None,
    ) -> str:
        task = self._load(tid)
        if status:
            task["status"] = status
            if status == "completed":
                for fp in TASKS_DIR.glob("task_*.json"):
                    t = json.loads(fp.read_text(encoding="utf-8"))
                    if tid in t.get("blockedBy", []):
                        t["blockedBy"].remove(tid)
                        self._save(t)
            if status == "deleted":
                (TASKS_DIR / f"task_{tid}.json").unlink(missing_ok=True)
                return f"任务 #{tid} 已删除"
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def list_all(self) -> str:
        tasks = [
            json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(TASKS_DIR.glob("task_*.json"))
        ]
        if not tasks:
            return "暂无看板任务。"
        lines = []
        for t in tasks:
            m = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(
                t["status"], "[?]"
            )
            owner = f" @{t['owner']}" if t.get("owner") else ""
            blocked = f"（依赖未满足: {t['blockedBy']}）" if t.get("blockedBy") else ""
            lines.append(f"{m} #{t['id']}: {t['subject']}{owner}{blocked}")
        return "\n".join(lines)

    def claim(self, tid: int, owner: str) -> str:
        with self._claim_lock:
            task = self._load(tid)
            if task.get("status") != "pending":
                return f"任务 #{tid} 当前状态为 {task.get('status')}，不可认领"
            if task.get("owner"):
                return f"任务 #{tid} 已被「{task.get('owner')}」认领"
            if task.get("blockedBy"):
                return f"任务 #{tid} 仍被依赖阻塞：{task.get('blockedBy')}"
            task["owner"] = owner
            task["status"] = "in_progress"
            self._save(task)
            return f"任务 #{tid} 已由「{owner}」认领"
