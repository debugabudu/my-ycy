---
name: subagent-default
description: 默认子代理配方：工作区四类工具，用于短时上下文隔离与可复用配置
kind: subagent
tools: bash, read_file, write_file, edit_file, load_skill
max_turns: 30
---

用于不需要单独建业务 profile 时的显式默认；需要只读探查可另建 `explore` 等 profile。
