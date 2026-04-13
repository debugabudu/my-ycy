from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProfile:
    name: str
    description: str
    kind: str  # subagent | teammate | both
    tools: list[str]
    system_template: str | None = None
    max_turns: int | None = None
    use_body_as_system: bool = False
    # Idle 时是否由运行时扫任务板并代抢单（仅当 tools 含 claim_task 时才会执行）
    auto_claim_tasks: bool = True
    body: str = ""

    def allows_subagent(self) -> bool:
        return self.kind in ("subagent", "both")

    def allows_teammate(self) -> bool:
        return self.kind in ("teammate", "both")
