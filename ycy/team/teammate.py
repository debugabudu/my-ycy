import json
import logging
import threading
import time

from ycy.agent.bundles import build_teammate_bundle_from_profile
from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.agent.profiles.prompting import resolve_teammate_system
from ycy.agent.tool_runner import (
    append_assistant,
    call_model,
    dispatch_tool_use_blocks,
    response_requested_idle,
)
from ycy.config import MODEL, TASKS_DIR, TEAM_DIR, WORKDIR, client
from ycy.constants import IDLE_TIMEOUT, POLL_INTERVAL
from ycy.observability.tracing import get_last_emitted_span_id
from ycy.tasks.board import TaskManager
from ycy.team.bus import MessageBus
from ycy.tools.handlers import make_tool_handlers

_log = logging.getLogger("ycy.team")


def _bundle_has_claim_task(bundle) -> bool:
    return any(s.get("name") == "claim_task" for s in bundle.tool_specs)


class TeammateManager:
    def __init__(
        self,
        bus: MessageBus,
        task_mgr: TaskManager,
        profile_loader: AgentProfileLoader | None = None,
        skills=None,
        todo=None,
        bg=None,
    ):
        TEAM_DIR.mkdir(exist_ok=True)
        self.bus = bus
        self.task_mgr = task_mgr
        self.profile_loader = profile_loader
        self._skills = skills
        self._todo = todo
        self._bg = bg
        self.config_path = TEAM_DIR / "config.json"
        self.config = self._load()
        self.threads = {}

    def _load(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {"team_name": "default", "members": []}

    def _save(self):
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _find(self, name: str) -> dict | None:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def spawn(
        self,
        name: str,
        role: str,
        prompt: str,
        profile: str | None = None,
        trace_parent_span_id: str | None = None,
    ) -> str:
        if not profile or not str(profile).strip():
            return (
                "错误：启动队友必须指定 profile（agents 中的专家配置 id）。"
                "通用模板可使用 teammate-default；简单隔离请用 task + 子代理 profile。"
            )
        if not self.profile_loader:
            return "错误：未加载 Agent 配置。"
        pid = str(profile).strip()
        p = self.profile_loader.get(pid)
        if not p:
            return (
                f"错误：未知的 Agent 配置「{pid}」。"
                f"可用：{', '.join(self.profile_loader.profiles.keys())}"
            )
        if not p.allows_teammate():
            return (
                f"错误：配置「{pid}」不能作为队友使用（kind={p.kind}）。"
            )

        member = self._find(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"错误：「{name}」当前状态为 {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save()
        threading.Thread(
            target=self._loop,
            args=(name, role, prompt, pid, trace_parent_span_id),
            daemon=True,
        ).start()
        return f"已启动队友「{name}」（角色：{role}）"

    def _set_status(self, name: str, status: str):
        member = self._find(name)
        if member:
            member["status"] = status
            self._save()

    def _handler_deps(self):
        """与 container 对齐的运行时依赖；缺省时回退到进程级单例。"""
        from ycy import container

        return (
            self._todo if self._todo is not None else container.TODO,
            self._skills if self._skills is not None else container.SKILLS,
            self.task_mgr,
            self._bg if self._bg is not None else container.BG,
            self.bus,
            self,
            self.profile_loader
            if self.profile_loader is not None
            else container.AGENTS,
        )

    def _loop(
        self,
        name: str,
        role: str,
        prompt: str,
        profile_name: str | None = None,
        trace_parent_span_id: str | None = None,
    ):
        team_name = self.config["team_name"]
        profile = (
            self.profile_loader.get(profile_name)
            if self.profile_loader and profile_name
            else None
        )
        if profile is None:
            _log.error("队友 %s 的 profile %r 无效或未加载，退出循环", name, profile_name)
            self._set_status(name, "shutdown")
            return

        sys_prompt = resolve_teammate_system(
            profile, name=name, role=role, team_name=team_name, workdir=WORKDIR
        )
        messages = [{"role": "user", "content": prompt}]
        todo, skills, task_mgr, bg, bus, team, agents = self._handler_deps()
        handlers = make_tool_handlers(
            todo, skills, task_mgr, bg, bus, team, agents, actor=name
        )
        bundle = build_teammate_bundle_from_profile(profile, handlers)
        auto_claim_runtime = profile.auto_claim_tasks and _bundle_has_claim_task(bundle)
        if not profile.auto_claim_tasks:
            _log.debug("Teammate %s: auto_claim_tasks=false (idle 仅 inbox)", name)
        elif not _bundle_has_claim_task(bundle):
            _log.debug("Teammate %s: bundle 无 claim_task，跳过 idle 自动抢单", name)
        chain_parent = trace_parent_span_id
        while True:
            for _ in range(50):
                inbox = self.bus.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                try:
                    response = call_model(
                        messages,
                        system=sys_prompt,
                        tool_specs=bundle.tool_specs,
                        client=client,
                        model=MODEL,
                        role="teammate",
                        parent_span_id=chain_parent,
                    )
                except Exception:
                    _log.exception("Teammate LLM failed name=%s", name)
                    self._set_status(name, "shutdown")
                    return
                chain_parent = get_last_emitted_span_id()
                append_assistant(messages, response)
                if response.stop_reason != "tool_use":
                    break
                sid = get_last_emitted_span_id()
                results = dispatch_tool_use_blocks(
                    response,
                    bundle.handlers,
                    log=lambda n, o: _log.info("[%s] %s: %s", name, n, str(o)[:120]),
                    trace_span_id=sid,
                    trace_role="teammate",
                )
                messages.append({"role": "user", "content": results})
                if response_requested_idle(response):
                    break
            self._set_status(name, "idle")
            resume = False
            for _ in range(IDLE_TIMEOUT // max(POLL_INTERVAL, 1)):
                time.sleep(POLL_INTERVAL)
                inbox = self.bus.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = []
                for fp in sorted(TASKS_DIR.glob("task_*.json")):
                    t = json.loads(fp.read_text(encoding="utf-8"))
                    if t.get("status") == "pending" and not t.get("owner") and not t.get(
                        "blockedBy"
                    ):
                        unclaimed.append(t)
                if unclaimed and auto_claim_runtime:
                    task = unclaimed[0]
                    self.task_mgr.claim(task["id"], name)
                    if len(messages) <= 3:
                        messages.insert(
                            0,
                            {
                                "role": "user",
                                "content": (
                                    f"<identity>You are '{name}', role: {role}, "
                                    f"team: {team_name}.</identity>"
                                ),
                            },
                        )
                        messages.insert(
                            1,
                            {
                                "role": "assistant",
                                "content": f"I am {name}. Continuing.",
                            },
                        )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                                f"{task.get('description', '')}</auto-claimed>"
                            ),
                        }
                    )
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Claimed task #{task['id']}. Working on it.",
                        }
                    )
                    resume = True
                    break
            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def list_all(self) -> str:
        if not self.config["members"]:
            return "暂无队友。"
        lines = [f"团队：{self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]
