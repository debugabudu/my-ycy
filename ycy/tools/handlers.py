import json
from typing import Any

from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.constants import LEAD_ACTOR_ID
from ycy.observability.tracing import get_last_emitted_span_id
from ycy.runtime.background_manager import BackgroundManager
from ycy.skills.loader import SkillLoader
from ycy.tasks.board import TaskManager
from ycy.tasks.todos import TodoManager
from ycy.team.bus import MessageBus
from ycy.team.protocols import handle_plan_review, handle_shutdown_request
from ycy.tools.filesystem import run_edit, run_read, run_write
from ycy.tools.shell import run_bash


def make_tool_handlers(
    todo: TodoManager,
    skills: SkillLoader,
    task_mgr: TaskManager,
    bg: BackgroundManager,
    bus: MessageBus,
    team: Any,
    agents: AgentProfileLoader,
    *,
    actor: str = LEAD_ACTOR_ID,
) -> dict:
    """与 definitions.TOOLS 一一对应的可调用表。

    actor（消息/任务归属 id）约定：
    - 主 agent：常量 LEAD_ACTOR_ID（当前为 ``\"lead\"``），与 agent_loop 里 read_inbox、tracing role 一致。
    - 队友：spawn 时传入的队员 name（每人独立收件箱 ``<name>.jsonl``）。
    - 子 agent：常量 SUBAGENT_ACTOR_ID（``\"subagent\"``），所有并行 task 共用同一收件箱，仅适合不与队友混用的消息。

    send_message / read_inbox / broadcast / claim_task 等凡涉及「我是谁」的，均使用该字符串作为发送方或归属方。
    """

    def task_fn(**kw):
        from ycy.agent.subagent import run_subagent

        return run_subagent(
            kw["prompt"],
            profile=kw.get("profile"),
            profiles=agents,
        )

    def idle_fn(**kw):
        return (
            "已进入空闲阶段。"
            if actor != LEAD_ACTOR_ID
            else "主控（lead）不使用 idle 工具。"
        )

    return {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
        "todo_write": lambda **kw: todo.update(kw["items"]),
        "task": task_fn,
        "load_skill": lambda **kw: skills.load(kw["name"]),
        "load_agent_profile": lambda **kw: agents.load_full(kw["name"]),
        "compress": lambda **kw: "已请求压缩上下文（由主循环在下一轮处理）。",
        "background_run": lambda **kw: bg.run(kw["command"], kw.get("timeout", 120)),
        "check_background": lambda **kw: bg.check(kw.get("task_id")),
        "task_create": lambda **kw: task_mgr.create(kw["subject"], kw.get("description", "")),
        "task_get": lambda **kw: task_mgr.get(kw["task_id"]),
        "task_update": lambda **kw: task_mgr.update(
            kw["task_id"], kw.get("status"), kw.get("add_blocked_by"), kw.get("add_blocks")
        ),
        "task_list": lambda **kw: task_mgr.list_all(),
        "spawn_teammate": lambda **kw: team.spawn(
            kw["name"],
            kw["role"],
            kw["prompt"],
            profile=kw.get("profile"),
            trace_parent_span_id=get_last_emitted_span_id(),
        ),
        "list_teammates": lambda **kw: team.list_all(),
        "send_message": lambda **kw: bus.send(
            actor, kw["to"], kw["content"], kw.get("msg_type", "message")
        ),
        "read_inbox": lambda **kw: json.dumps(bus.read_inbox(actor), indent=2),
        "broadcast": lambda **kw: bus.broadcast(actor, kw["content"], team.member_names()),
        "shutdown_request": lambda **kw: handle_shutdown_request(bus, kw["teammate"]),
        "plan_approval": lambda **kw: handle_plan_review(
            bus, kw["request_id"], kw["approve"], kw.get("feedback", "")
        ),
        "idle": idle_fn,
        "claim_task": lambda **kw: task_mgr.claim(kw["task_id"], actor),
    }
