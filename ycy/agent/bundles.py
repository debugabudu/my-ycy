"""ToolBundle：schema 来自 catalog；handlers 由 tools.handlers.make_tool_handlers 切片装配。

子代理 / 队友的**创建入口**已在 subagent.py、teammate.py 强制要求 profile；
本模块负责：profile 声明的 tools ∪ 下列隐式集合 → 最终可见工具列表。
"""

from ycy.agent.profiles.models import AgentProfile
from ycy.agent.tool_bundle import ToolBundle
from ycy.tools.catalog import TOOL_SPEC_BY_NAME

# 队友：协作与看板相关，合并进任意队友 profile，不必在 AGENT.md 的 tools 里重复写
TEAMMATE_IMPLICIT_TOOLS = frozenset(
    {
        "send_message",
        "read_inbox",
        "broadcast",
        "shutdown_request",
        "plan_approval",
        "idle",
        "claim_task",
    }
)

# 队友：工作区 + 按需 Skill，与上式一并并入每个队友 bundle
TEAMMATE_BASE_TOOLS = TEAMMATE_IMPLICIT_TOOLS | frozenset(
    {"bash", "read_file", "write_file", "edit_file", "load_skill"}
)

# 子代理：任意 profile 都会并入 load_skill（不必在 profile 里写）
SUBAGENT_ALWAYS_TOOLS = frozenset({"load_skill"})

# profile.tools 过滤后为空时的回退（畸形配置或仅未知工具名）
_DEFAULT_SUBAGENT_FALLBACK = frozenset({"bash", "read_file", "write_file", "edit_file"})


def _specs_for(names: list[str]) -> list[dict]:
    return [TOOL_SPEC_BY_NAME[n] for n in names if n in TOOL_SPEC_BY_NAME]


def _bundle(names: list[str], handlers: dict) -> ToolBundle:
    specs = _specs_for(names)
    h = {n: handlers[n] for n in names if n in handlers}
    return ToolBundle(tool_specs=specs, handlers=h)


def _default_subagent_bundle(handlers: dict) -> ToolBundle:
    names = sorted(_DEFAULT_SUBAGENT_FALLBACK | SUBAGENT_ALWAYS_TOOLS)
    return _bundle(names, handlers)


def build_subagent_bundle_from_profile(profile: AgentProfile, handlers: dict) -> ToolBundle:
    names = set(t for t in profile.tools if t in TOOL_SPEC_BY_NAME)
    names |= SUBAGENT_ALWAYS_TOOLS
    if not (names - SUBAGENT_ALWAYS_TOOLS):
        return _default_subagent_bundle(handlers)
    return _bundle(sorted(names), handlers)


def build_teammate_bundle_from_profile(profile: AgentProfile, handlers: dict) -> ToolBundle:
    names = set(profile.tools) & TOOL_SPEC_BY_NAME.keys()
    names |= TEAMMATE_BASE_TOOLS
    return _bundle(sorted(names), handlers)
