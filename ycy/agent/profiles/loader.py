import logging
from pathlib import Path

from ycy.agent.profiles.models import AgentProfile
from ycy.agent.profiles.validate import filter_unknown_tools
from ycy.content.frontmatter import parse_agent_meta_lines, split_frontmatter

_log = logging.getLogger("ycy.agent.profiles")


class AgentProfileLoader:
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.profiles: dict[str, AgentProfile] = {}
        if agents_dir.exists():
            for f in sorted(agents_dir.rglob("AGENT.md")):
                text = f.read_text()
                raw_meta, body = split_frontmatter(text)
                meta_raw: dict = {}
                if raw_meta is not None:
                    meta_raw = parse_agent_meta_lines(raw_meta)
                else:
                    _log.warning("Skip agent profile without frontmatter: %s", f)
                    continue
                name = str(meta_raw.get("name", f.parent.name))
                tools_in = meta_raw.get("tools")
                if not isinstance(tools_in, list):
                    tools_in = []
                kind = str(meta_raw.get("kind", "both")).strip().lower()
                if kind not in ("subagent", "teammate", "both"):
                    kind = "both"
                tools = filter_unknown_tools(tools_in, profile_name=name, path=str(f))
                max_turns = meta_raw.get("max_turns")
                if max_turns is not None and not isinstance(max_turns, int):
                    max_turns = None
                st = meta_raw.get("system_template") or meta_raw.get("system")
                system_template = str(st).strip() if st else None
                use_body = bool(meta_raw.get("use_body_as_system", False))
                ac = meta_raw.get("auto_claim_tasks")
                if ac is None:
                    auto_claim_tasks = True
                else:
                    auto_claim_tasks = bool(ac)
                self.profiles[name] = AgentProfile(
                    name=name,
                    description=str(meta_raw.get("description", "-")),
                    kind=kind,
                    tools=tools,
                    system_template=system_template,
                    max_turns=max_turns,
                    use_body_as_system=use_body,
                    auto_claim_tasks=auto_claim_tasks,
                    body=body,
                )

    def descriptions(self) -> str:
        if not self.profiles:
            return "（当前未加载任何 Agent 配置）"
        return "\n".join(
            f"  - {n}: {p.description} [类型={p.kind}, 工具={','.join(p.tools) or '-'}, "
            f"空闲自动抢单={p.auto_claim_tasks}]"
            for n, p in self.profiles.items()
        )

    def get(self, name: str) -> AgentProfile | None:
        return self.profiles.get(name)

    def load_full(self, name: str) -> str:
        p = self.profiles.get(name)
        if not p:
            return (
                f"错误：未知的 Agent 配置「{name}」。可用：{', '.join(self.profiles.keys())}"
            )
        meta_lines = [
            f"name: {p.name}",
            f"description: {p.description}",
            f"kind: {p.kind}",
            f"tools: {', '.join(p.tools)}",
        ]
        if p.max_turns is not None:
            meta_lines.append(f"max_turns: {p.max_turns}")
        if p.system_template:
            meta_lines.append(f"system_template: {p.system_template}")
        meta_lines.append(f"use_body_as_system: {p.use_body_as_system}")
        meta_lines.append(f"auto_claim_tasks: {p.auto_claim_tasks}")
        header = "\n".join(meta_lines)
        body_section = p.body if p.body else "（无正文）"
        return f'<agent_profile name="{p.name}">\n---\n{header}\n---\n\n{body_section}\n</agent_profile>'
