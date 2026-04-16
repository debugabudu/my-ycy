import uuid

from ycy.agent.bundles import build_subagent_bundle_from_profile
from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.agent.prompts import BUILTIN_SUBAGENT_SYSTEM
from ycy.agent.profiles.prompting import resolve_subagent_system
from ycy.agent.tool_runner import run_tool_agent_session, summarize_text_response
from ycy.config import MODEL, WORKDIR, client
from ycy.constants import SUBAGENT_ACTOR_PREFIX, SUBAGENT_MAX_TURNS_DEFAULT
from ycy.observability.tracing import get_last_emitted_span_id


def run_subagent(
    prompt: str,
    profile: str | None = None,
    *,
    profiles: AgentProfileLoader | None = None,
) -> str:
    from ycy import container
    from ycy.tools.handlers import make_tool_handlers

    agents = profiles if profiles is not None else container.AGENTS
    actor_id = f"{SUBAGENT_ACTOR_PREFIX}-{uuid.uuid4().hex[:8]}"
    handlers = make_tool_handlers(
        container.TODO,
        container.SKILLS,
        container.TASK_MGR,
        container.BG,
        container.BUS,
        container.TEAM,
        agents,
        container.MEMORY,
        container.VECTOR,
        actor=actor_id,
    )

    if not profile or not str(profile).strip():
        return (
            "错误：子代理必须指定 profile（agents 下 AGENT.md 的 id），用于工具边界与提示复用。"
            "无特殊需求请使用 subagent-default。"
        )
    if not agents.profiles:
        return "错误：未加载 Agent 配置（agents 目录为空或未就绪）。"
    pid = str(profile).strip()
    p = agents.get(pid)
    if not p or not p.allows_subagent():
        return (
            f"错误：未知或不可用于子代理的配置「{pid}」。"
            f"可用：{', '.join(agents.profiles.keys())}"
        )
    bundle = build_subagent_bundle_from_profile(p, handlers)
    system = resolve_subagent_system(p, WORKDIR) or BUILTIN_SUBAGENT_SYSTEM
    max_turns = p.max_turns or SUBAGENT_MAX_TURNS_DEFAULT

    anchor = get_last_emitted_span_id()
    messages = [{"role": "user", "content": prompt}]
    resp = run_tool_agent_session(
        messages,
        system=system,
        tool_specs=bundle.tool_specs,
        handlers=bundle.handlers,
        client=client,
        model=MODEL,
        max_turns=max_turns,
        role="subagent",
        trace_parent_span_id=anchor,
    )
    return summarize_text_response(resp, empty="（子代理未返回有效内容）")
