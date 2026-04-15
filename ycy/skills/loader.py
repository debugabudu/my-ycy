from pathlib import Path

from ycy.content.frontmatter import parse_simple_meta_lines, split_frontmatter


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        if skills_dir.exists():
            for f in sorted(skills_dir.rglob("SKILL.md")):
                text = f.read_text(encoding="utf-8", errors="replace")
                raw_meta, body = split_frontmatter(text)
                if raw_meta is not None:
                    meta = parse_simple_meta_lines(raw_meta)
                else:
                    meta = {}
                name = meta.get("name", f.parent.name)
                self.skills[name] = {"meta": meta, "body": body}

    def descriptions(self) -> str:
        if not self.skills:
            return "（当前未加载任何 Skill）"
        return "\n".join(
            f"  - {n}: {s['meta'].get('description', '-')}" for n, s in self.skills.items()
        )

    def load(self, name: str) -> str:
        s = self.skills.get(name)
        if not s:
            return (
                f"错误：未知的 Skill「{name}」。可用：{', '.join(self.skills.keys())}"
            )
        return f'<skill name="{name}">\n{s["body"]}\n</skill>'
