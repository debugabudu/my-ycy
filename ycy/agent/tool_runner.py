import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from ycy.observability.tracing import (
    get_last_emitted_span_id,
    log_llm_response,
    log_llm_request,
    log_tool_execute,
    record_emitted_span,
)

_log = logging.getLogger("ycy.llm")


def dispatch_tool_use_blocks(
    response: Any,
    handlers: dict[str, Callable[..., str]],
    *,
    unknown_template: str = "未知工具：{name}",
    max_output_len: int = 50000,
    log: Callable[[str, str], None] | None = None,
    trace_span_id: str | None = None,
    trace_role: str = "lead",
) -> list[dict]:
    """把一轮 assistant 的 tool_use 块变成 tool_result 内容块列表。"""
    results: list[dict] = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        handler = handlers.get(block.name)
        t0 = time.time()
        err: str | None = None
        try:
            if handler:
                output = handler(**block.input)
            else:
                output = unknown_template.format(name=block.name)
        except Exception as e:
            err = str(e)
            output = f"错误：{e}"
        duration_ms = (time.time() - t0) * 1000
        if log:
            log(block.name, str(output))
        if trace_span_id:
            try:
                inp = str(block.input)[:2000]
            except Exception:
                inp = "(unserializable)"
            log_tool_execute(
                span_id=trace_span_id,
                role=trace_role,
                tool_name=block.name,
                input_preview=inp,
                output_preview=str(output)[:2000],
                duration_ms=duration_ms,
                error=err,
            )
        results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output)[:max_output_len],
            }
        )
    return results


def response_requested_idle(response: Any) -> bool:
    return any(
        getattr(b, "type", None) == "tool_use" and getattr(b, "name", None) == "idle"
        for b in response.content
    )


def call_model(
    messages: list,
    *,
    system: str | None,
    tool_specs: list[dict],
    client: Any,
    model: str,
    max_tokens: int = 8000,
    role: str = "lead",
    parent_span_id: str | None = None,
):
    span_id = uuid.uuid4().hex[:12]
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "tools": tool_specs,
        "max_tokens": max_tokens,
    }
    if system is not None:
        kwargs["system"] = system
    log_llm_request(
        span_id=span_id,
        parent_span_id=parent_span_id,
        role=role,
        model=model,
        num_messages=len(messages),
        num_tools=len(tool_specs),
        max_tokens=max_tokens,
    )
    t0 = time.time()
    try:
        resp = client.messages.create(**kwargs)
    except Exception:
        _log.exception("messages.create failed role=%s", role)
        raise
    duration_ms = (time.time() - t0) * 1000
    tool_names = [
        b.name for b in resp.content if getattr(b, "type", None) == "tool_use"
    ]
    log_llm_response(
        span_id=span_id,
        role=role,
        stop_reason=resp.stop_reason,
        tool_use_names=tool_names,
        duration_ms=duration_ms,
    )
    record_emitted_span(span_id)
    return resp


def append_assistant(messages: list, response: Any) -> None:
    messages.append({"role": "assistant", "content": response.content})


def run_tool_agent_session(
    messages: list,
    *,
    system: str | None,
    tool_specs: list[dict],
    handlers: dict[str, Callable[..., str]],
    client: Any,
    model: str,
    max_turns: int,
    max_tokens: int = 8000,
    log: Callable[[str, str], None] | None = None,
    unknown_template: str = "未知工具：{name}",
    max_tool_output_len: int = 50000,
    role: str = "subagent",
    trace_parent_span_id: str | None = None,
) -> Any | None:
    last = None
    chain_parent = trace_parent_span_id
    for _ in range(max_turns):
        last = call_model(
            messages,
            system=system,
            tool_specs=tool_specs,
            client=client,
            model=model,
            max_tokens=max_tokens,
            role=role,
            parent_span_id=chain_parent,
        )
        chain_parent = get_last_emitted_span_id()
        append_assistant(messages, last)
        if last.stop_reason != "tool_use":
            break
        sid = get_last_emitted_span_id()
        results = dispatch_tool_use_blocks(
            last,
            handlers,
            unknown_template=unknown_template,
            max_output_len=max_tool_output_len,
            log=log,
            trace_span_id=sid,
            trace_role=role,
        )
        messages.append({"role": "user", "content": results})
    return last


def summarize_text_response(response: Any | None, *, empty: str = "(no summary)") -> str:
    if not response:
        return empty
    return "".join(b.text for b in response.content if hasattr(b, "text")) or empty
