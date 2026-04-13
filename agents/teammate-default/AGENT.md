---
name: teammate-default
description: 通用专家队友模板（协作 + 看板）；多专家并行/串行协作时再 spawn
kind: teammate
tools: bash, read_file, write_file, edit_file, load_skill
auto_claim_tasks: true
---

长期运行、消耗更多资源；仅在需要独立专家线程与消息协作时使用。简单子任务请优先用 `task` + subagent profile。
