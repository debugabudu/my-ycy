"""主 Agent definitions 中的工具 schema 索引，供 profile 按名称装配。"""

from ycy.tools.definitions import TOOLS

TOOL_SPEC_BY_NAME: dict[str, dict] = {t["name"]: t for t in TOOLS}
