import json
import logging

from ycy.agent.tool_runner import append_assistant, call_model, dispatch_tool_use_blocks
from ycy.config import MODEL, client
from ycy.constants import LEAD_ACTOR_ID, TOKEN_THRESHOLD
from ycy.context import auto_compact, estimate_tokens, microcompact
from ycy.observability.tracing import get_last_emitted_span_id
from ycy.tools.definitions import TOOLS

_log = logging.getLogger("ycy.agent")


def agent_loop(messages: list):
    from ycy import container

    rounds_without_todo = 0
    chain_parent = None
    while True:
        microcompact(messages)
        if estimate_tokens(messages) > TOKEN_THRESHOLD:
            _log.info("Auto-compact triggered (token threshold)")
            messages[:] = auto_compact(messages)
        notifs = container.BG.drain()
        if notifs:
            txt = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"<background-results>\n{txt}\n</background-results>",
                }
            )
            messages.append(
                {"role": "assistant", "content": "已记录后台任务结果。"}
            )
        inbox = container.BUS.read_inbox(LEAD_ACTOR_ID)
        if inbox:
            messages.append(
                {"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"}
            )
            messages.append({"role": "assistant", "content": "已记录收件箱消息。"})
        response = call_model(
            messages,
            system=container.SYSTEM,
            tool_specs=TOOLS,
            client=client,
            model=MODEL,
            role="lead",
            parent_span_id=chain_parent,
        )
        chain_parent = get_last_emitted_span_id()
        append_assistant(messages, response)
        if response.stop_reason != "tool_use":
            return
        used_names = [
            b.name for b in response.content if getattr(b, "type", None) == "tool_use"
        ]
        manual_compress = "compress" in used_names
        used_todo = "todo_write" in used_names
        sid = get_last_emitted_span_id()
        results = dispatch_tool_use_blocks(
            response,
            container.TOOL_HANDLERS,
            log=lambda n, o: _log.info("%s: %s", n, str(o)[:200]),
            trace_span_id=sid,
            trace_role="lead",
        )
        rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
        if container.TODO.has_open_items() and rounds_without_todo >= 3:
            results.insert(
                0,
                {"type": "text", "text": "<reminder>请更新你的 todo_write 待办列表。</reminder>"},
            )
        messages.append({"role": "user", "content": results})
        if manual_compress:
            _log.info("Manual compress after compress tool")
            messages[:] = auto_compact(messages)
