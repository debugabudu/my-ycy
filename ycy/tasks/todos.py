class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        validated, ip = [], 0
        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            if not content:
                raise ValueError(f"第 {i} 项：缺少 content")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"第 {i} 项：非法 status「{status}」")
            af = str(item.get("activeForm", "")).strip() or content
            if status == "in_progress":
                ip += 1
            validated.append({"content": content, "status": status, "activeForm": af})
        if len(validated) > 20:
            raise ValueError("待办最多 20 条")
        if ip > 1:
            raise ValueError("仅允许一条 in_progress 状态")
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "暂无待办。"
        lines = []
        for item in self.items:
            m = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}.get(
                item["status"], "[?]"
            )
            af, ct = item["activeForm"], item["content"]
            suffix = (
                f" <- {af}"
                if item["status"] == "in_progress" and af != ct
                else ""
            )
            lines.append(f"{m} {item['content']}{suffix}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n（已完成 {done}/{len(self.items)}）")
        return "\n".join(lines)

    def has_open_items(self) -> bool:
        return any(item.get("status") != "completed" for item in self.items)
