import logging

from ycy.tools.catalog import TOOL_SPEC_BY_NAME

_log = logging.getLogger("ycy.agent.profiles")


def filter_unknown_tools(
    tools: list[str], *, profile_name: str, path: str
) -> list[str]:
    """只剔除在 definitions.TOOLS 中不存在的工具名；不再按 kind 做白名单。"""
    unknown = [t for t in tools if t not in TOOL_SPEC_BY_NAME]
    if unknown:
        _log.warning(
            "配置 %r（%s）：以下工具不在 definitions.TOOLS 中，已忽略：%s",
            profile_name,
            path,
            unknown,
        )
    return [t for t in tools if t in TOOL_SPEC_BY_NAME]
