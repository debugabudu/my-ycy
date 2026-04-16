import json
from pathlib import Path
from typing import Any

from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.constants import LEAD_ACTOR_ID
from ycy.memory_store import MemoryStore
from ycy.memory_vector import VectorStore
from ycy.observability.tracing import get_last_emitted_span_id
from ycy.runtime.background_manager import BackgroundManager
from ycy.skills.loader import SkillLoader
from ycy.skills.draft import draft_skill_from_latest_session
from ycy.tasks.board import TaskManager
from ycy.tasks.todos import TodoManager
from ycy.team.bus import MessageBus
from ycy.team.protocols import handle_plan_review, handle_shutdown_request
from ycy.tools.filesystem import run_edit, run_read, run_restore_backup, run_write
from ycy.tools.shell import run_bash
from ycy.tools.time_utils import run_current_time
from ycy.tools.web_search import run_web_search


def make_tool_handlers(
    todo: TodoManager,
    skills: SkillLoader,
    task_mgr: TaskManager,
    bg: BackgroundManager,
    bus: MessageBus,
    team: Any,
    agents: AgentProfileLoader,
    memory: MemoryStore,
    vector: VectorStore,
    *,
    actor: str = LEAD_ACTOR_ID,
) -> dict:
    """与 definitions.TOOLS 一一对应的可调用表。

    actor（消息/任务归属 id）约定：
    - 主 agent：常量 LEAD_ACTOR_ID（当前为 ``\"lead\"``），与 agent_loop 里 read_inbox、tracing role 一致。
    - 队友：spawn 时传入的队员 name（每人独立收件箱 ``<name>.jsonl``）。
    - 子 agent：每次 task 运行使用独立 actor id（形如 ``subagent-<id>``），避免并行收件箱串扰。

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

    def memory_append_fn(**kw):
        entry = memory.append(
            text=kw["text"],
            source=kw.get("source", "user_note"),
            run_id=kw.get("run_id"),
            summary=kw.get("summary"),
            tags=kw.get("tags") or [],
            anchors=kw.get("anchors") or [],
            importance=kw.get("importance", 3),
        )
        # 高重要级条目自动进入 memories 向量索引
        if entry.importance >= 3:
            vector.upsert_text(
                namespace="memories",
                text=entry.summary or entry.text,
                ref_type="memory",
                ref_id=entry.id,
                meta={"tags": entry.tags, "anchors": entry.anchors},
            )
        return json.dumps(entry.__dict__, ensure_ascii=False, indent=2)

    def memory_search_fn(**kw):
        rows = memory.search(
            query=kw.get("query", ""),
            tags=kw.get("tags"),
            from_time=kw.get("from_time"),
            to_time=kw.get("to_time"),
            limit=kw.get("limit", 10),
        )
        payload = [r.__dict__ for r in rows]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def memory_compact_fn(**kw):
        out = memory.compact(
            max_entries=kw.get("max_entries", 500),
            preserve_anchors=kw.get("preserve_anchors", True),
        )
        return json.dumps(out, ensure_ascii=False, indent=2)

    def skill_draft_from_chat_fn(**kw):
        from ycy import config

        path = draft_skill_from_latest_session(
            skills_dir=config.SKILLS_DIR,
            name=kw["name"],
            focus=kw.get("focus", ""),
            n_rounds=kw.get("n_rounds", 6),
            overwrite=kw.get("overwrite", False),
        )
        return json.dumps(
            {"status": "ok", "path": str(path), "name": kw["name"]},
            ensure_ascii=False,
            indent=2,
        )

    def skill_index_memory_fn(**kw):
        name = kw["name"]
        namespace = kw.get("namespace", "skills")
        max_chunks = max(1, min(20, int(kw.get("max_chunks", 8))))
        s = skills.skills.get(name)
        if not s:
            raise ValueError(f"未知 Skill：{name}")
        body = s["body"]
        # 以二级标题/空行粗切，索引关键片段
        chunks = [p.strip() for p in body.split("\n\n") if p.strip()]
        picked = chunks[:max_chunks]
        out = []
        for i, ch in enumerate(picked):
            entry = memory.append(
                text=ch,
                source="skill",
                tags=[f"skill:{name}"],
                anchors=[name],
                importance=3,
                summary=f"{name} 片段 #{i+1}",
            )
            item_id = vector.upsert_text(
                namespace=namespace,
                text=ch,
                ref_type="skill_chunk",
                ref_id=entry.id,
                meta={"skill": name, "chunk": i + 1},
            )
            out.append({"memory_id": entry.id, "vector_item_id": item_id})
        return json.dumps(
            {"skill": name, "namespace": namespace, "indexed": len(out), "items": out},
            ensure_ascii=False,
            indent=2,
        )

    def vector_index_fn(**kw):
        namespace = kw.get("namespace", "notes")
        if "path" in kw and kw["path"]:
            return json.dumps(
                vector.index_directory(namespace=namespace, directory=Path(kw["path"])),
                ensure_ascii=False,
                indent=2,
            )
        if "text" in kw and kw["text"]:
            item_id = vector.upsert_text(
                namespace=namespace,
                text=kw["text"],
                ref_type=kw.get("ref_type", "manual"),
                ref_id=kw.get("ref_id"),
                meta=kw.get("meta") or {},
            )
            return json.dumps({"namespace": namespace, "item_id": item_id}, ensure_ascii=False)
        raise ValueError("vector_index 需要 path 或 text 参数")

    def vector_search_fn(**kw):
        out = vector.search(
            namespace=kw.get("namespace", "notes"),
            query=kw["query"],
            top_k=kw.get("top_k", 5),
            min_score=kw.get("min_score", 0.05),
        )
        return json.dumps(out, ensure_ascii=False, indent=2)

    return {
        "current_time": lambda **kw: run_current_time(),
        "web_search": lambda **kw: run_web_search(
            kw["query"],
            count=kw.get("count", 8),
            search_engine=kw.get("search_engine", "search_std"),
            search_domain_filter=kw.get("search_domain_filter"),
            search_recency_filter=kw.get("search_recency_filter", "noLimit"),
            content_size=kw.get("content_size", "medium"),
        ),
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
        "restore_file_backup": lambda **kw: run_restore_backup(kw["path"], kw["backup_path"]),
        "todo_write": lambda **kw: todo.update(kw["items"]),
        "task": task_fn,
        "load_skill": lambda **kw: skills.load(kw["name"], mode=kw.get("mode", "full")),
        "skill_draft_from_chat": skill_draft_from_chat_fn,
        "skill_index_memory": skill_index_memory_fn,
        "load_agent_profile": lambda **kw: agents.load_full(kw["name"]),
        "compress": lambda **kw: "已请求压缩上下文（由主循环在下一轮处理）。",
        "memory_append": memory_append_fn,
        "memory_search": memory_search_fn,
        "memory_compact": memory_compact_fn,
        "vector_index": vector_index_fn,
        "vector_search": vector_search_fn,
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
