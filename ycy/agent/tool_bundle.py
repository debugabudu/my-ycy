from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolBundle:
    """一组对外暴露给模型的工具：API schema + 本地 handler（name -> callable）。"""

    tool_specs: list[dict]
    handlers: dict[str, Callable[..., str]] = field(default_factory=dict)

    def merge(self, other: "ToolBundle") -> "ToolBundle":
        seen = {t["name"] for t in self.tool_specs}
        extra_specs = [t for t in other.tool_specs if t["name"] not in seen]
        merged_handlers = {**other.handlers, **self.handlers}
        return ToolBundle(
            tool_specs=[*self.tool_specs, *extra_specs],
            handlers=merged_handlers,
        )
