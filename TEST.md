# ycy 能力测试用例（Prompt 清单）

以下用例供 **人工在 `python ycy.py` 的 REPL 中**粘贴或改写后发送给模型，用于覆盖当前工具与行为。模型是否严格按工具调用取决于具体模型；若未触发某工具，可收紧指令（明确写出「请调用 xxx 工具」）。

**前置**

- 已在项目根配置 `.env`（`MODEL_ID` 等），并在目标工作目录启动 `ycy.py`。
- 若仓库中尚无自定义 Skill，请先完成 **用例 S0**，否则 `load_skill` 类用例会失败。

---

## S0. 准备最小 Skill（覆盖 `load_skill`）

在仓库中新建文件（示例路径，可改 id）：

`skills/demo-skill/SKILL.md`

```markdown
---
name: demo-skill
description: 测试用 Skill，说明 ycy 如何加载正文
---

# demo-skill

这是一条测试 Skill。请用一句话确认你已读过本文，并说明 Skill 名称。
```

重启 `ycy.py` 后使用本节末尾 **「L1 — 主会话 load_skill」** 用例。

---

## 工作区工具

### W1 — `read_file`

```text
请使用 read_file 工具读取 README.md 的前 30 行（如有 limit 参数请使用），并概括项目用途。
```

### W2 — `bash`

```text
请使用 bash 工具执行：python3 -c "print('ycy-bash-ok')"，并把输出原样告诉我。
```

### W3 — `write_file` + `edit_file`

```text
请先用 write_file 在工作区根目录创建临时文件 _ycy_test.txt，内容为单行 hello-ycy；
再用 edit_file 把 hello-ycy 改成 hello-ycy-edited；
最后用 read_file 读回文件内容确认。
```

---

## 会话待办

### T1 — `todo_write`

```text
请用 todo_write 更新待办：两条 pending，一条 in_progress（content 与 activeForm 可自拟）；再读当前待办状态并说明。
```

---

## 子代理 `task`（必填 profile）

### A1 — 使用 `subagent-default`

```text
请使用 task 工具：profile 填 subagent-default，prompt 为「列出当前目录下文件名（用 bash），不要改任何文件」，把子代理返回摘要给我。
```

### A2 — 子代理 + Skill（需 S0）

```text
请使用 task 工具，profile 仍为 subagent-default，prompt 为：先 load_skill 加载 demo-skill，再按 Skill 要求回复一句话。
```

---

## Agent 配置

### P1 — `load_agent_profile`

```text
请使用 load_agent_profile 工具加载名为 subagent-default 的配置，并简要说明其 kind 与 tools 列表要点（基于返回内容）。
```

---

## 上下文压缩

### C1 — `compress`

```text
请使用 compress 工具，并说明接下来主循环可能会如何压缩上下文（根据你对系统的理解简要说明即可）。
```

---

## 后台命令

### B1 — `background_run` + `check_background`

```text
请使用 background_run 在后台执行一条耗时很短命令（例如 sleep 1 && echo bg-done），记下返回的 task_id；
稍等几秒后用 check_background 查询该 task_id，把状态与输出摘要告诉我。
```

---

## 看板任务（`.tasks`）

### K1 — 全流程

```text
请依次使用工具：task_create 创建标题为「ycy测试任务」、描述随意的任务；
task_list 查看列表并记下新任务 id；
task_get 拉取该 id 详情；
task_update 将状态改为 in_progress；
再用 claim_task 以当前 lead 身份认领该任务（如工具允许）；
最后 task_update 将状态改为 completed 或 deleted（二选一，并说明原因）。
```

（若 `claim_task` 与当前看板状态冲突，以 `task_list` / `task_get` 实际状态为准调整步骤。）

---

## 团队与消息总线

### M1 — `list_teammates`

```text
请先使用 list_teammates 查看当前团队状态并汇报。
```

### M2 — `spawn_teammate`（需 profile）

```text
请使用 spawn_teammate：name 填 testmate1，role 填「测试专家」，prompt 填「收到启动提示后，用 send_message 给 lead 发一条简短中文问候」，profile 必须使用 teammate-default。
```

（队友在后台线程运行；可稍后发 **M3** 或 `/inbox` 查看 lead 收件箱。）

### M3 — `read_inbox` / `send_message`（lead）

```text
请使用 read_inbox（以当前 lead 身份）查看是否有新消息；若有，概括内容；若没有，说明为空。如需回复队友，可用 send_message 向 testmate1 发一条简短回复。
```

### M4 — `broadcast`

```text
若当前存在至少一名队友，请使用 broadcast 向所有队友发一条广播测试消息；若无队友，请先说明需先 spawn_teammate。
```

### M5 — `shutdown_request`

```text
若存在名为 testmate1 的队友，请使用 shutdown_request 请求其关闭，并说明返回结果；若不存在该队友，请说明跳过。
```

### M6 — `plan_approval`（可选 / 依赖运行时是否注册计划请求）

```text
若你知晓当前有效的 plan request_id，请演示 plan_approval 的调用；若当前没有待审批计划，请说明 plan_approval 通常需队友与协议配合产生 request_id，本项跳过。
```

（当前实现中 `plan_requests` 需业务侧写入；无现成 id 时跳过属正常。）

---

## 队友侧行为（需已 spawn）

以下需在 **已启动队友** 后观察日志或后续消息；也可作为你手动验证的检查项：

### TM1 — 队友是否会用 `idle`

队友在完成任务后可能调用 `idle` 进入空闲；你可从 `/team` 状态或日志观察。

### TM2 — `claim_task`（队友身份）

若看板存在 `pending` 且无 owner 的任务，且队友 profile 含 `claim_task` 且 `auto_claim_tasks` 为 true，空闲时可能自动认领；也可在测试说明中要求队友显式 claim（依赖模型行为）。

---

## 主 Agent 对 `idle`（预期非致命）

### I1

```text
请调用 idle 工具一次，并把工具返回原文告诉我。
```

预期：返回说明 lead 不使用 idle 的文案（见 `handlers.py`）。

---

## 回归：组合场景

### R1

```text
请用 todo_write 记两条待办，用 task_create 建一个看板任务，再用 task 工具（profile=subagent-default）让子代理只读确认 README.md 是否存在，最后 task_list 汇总当前看板。
```

---

## 检查清单（自检）

| 能力 | 用例编号 |
|------|----------|
| read_file / write_file / edit_file / bash | W1–W3 |
| todo_write | T1 |
| task + profile | A1, A2 |
| load_skill | S0 + L1（在 A2 或单独 L1） |
| load_agent_profile | P1 |
| compress | C1 |
| background_run / check_background | B1 |
| task_create / get / update / list / claim | K1 |
| spawn_teammate / list_teammates | M2, M1 |
| send_message / read_inbox / broadcast | M3, M4 |
| shutdown_request | M5 |
| plan_approval | M6（可选） |
| idle（lead） | I1 |

### L1 — 主会话 `load_skill`（依赖 S0）

```text
请先使用 load_skill 加载 demo-skill，然后严格按 Skill 正文要求回复。
```

---

## 智能调度与隐性意图（勿在 prompt 中点名工具）

以下用例**刻意不写**「请调用 xxx 工具」「请 spawn」「请 task_create」等字样，用于观察模型是否会**自主**选择：读文件、拆待办、建看板任务、起子代理或队友、发消息等。评测时可结合日志或 `.trace/*.jsonl` 中的 `tool_execute` 记录。

**建议评法（人工）**

- **优**：在合理步数内完成目标，且工具链与目标一致（例如先读后改、复杂探查用子代理、多角色协作起队友）。
- **中**：完成目标但路径迂迴（如全程裸 `bash` 可完成却更安全应用 `read_file`）。
- **差**：拒绝行动、空泛建议、或明显该隔离/该记看板却全程闲聊。

### Z1 — 陌生文件先读后答

```text
我这个仓库里有个 README.md，里面主要讲了什么？用两三句话告诉我，并说明你是否真的打开过文件内容。
```

（期望：优先 `read_file` 或等价可靠方式，而非纯猜测。）

### Z2 — 多步骤小需求（待办 / 看板是否自发出现）

```text
我想给这个项目加一个简单的健康检查：在 README 末尾加一行「状态：OK」的占位说明。请你规划并执行，最后告诉我你改了什么；如果中间步骤多，希望你用合适的方式自己跟踪进度。
```

（期望：可能 `todo_write` 和/或 `task_create`；至少应 `read_file` + `edit_file`/`write_file`。）

### Z3 — 应用层「审计」子任务（是否用子代理隔离）

```text
请帮我在不动任何业务代码的前提下，统计一下 ycy 包里有多少个 .py 文件、各自大概多少行（给出总数和粗略分布即可）。我不想让主对话上下文塞满所有文件路径。
```

（期望：倾向用 `task` + `subagent-default` 或 `bash`/`read_file` 组合；考察是否意识到上下文隔离。）

### Z4 — 协作场景（是否起队友）

```text
我接下来要去开会 30 分钟。希望有一个「独立助手」在后台盯着：如果 `.tasks` 里出现新的 pending 任务，就给我（lead）发一条消息概括任务标题。现在仓库里可能还没有任务，你先帮我把环境准备好，并说明你会怎么实现「盯着」这件事。
```

（期望：可能 `spawn_teammate` + `teammate-default`、建一条测试任务、或至少解释用队友+收件箱；不要求一次做对，看思路与工具选择。）

### Z5 — 长命令不阻塞（后台意识）

```text
假设需要在工作区执行一条可能要跑 2 分钟的命令（你可以自己选一条安全且确实稍慢的，例如遍历大量小文件统计）。我希望主对话不要卡死等它结束，你安排一下怎么做并汇报结果。
```

（期望：倾向 `background_run` + `check_background`，而非长时间占用单轮。）

### Z6 — 知识包是否存在（Skill 主动性）

```text
如果这个项目里定义了名为 demo-skill 的 Skill，请按它的说明做；如果没有，请告诉我没有，并建议我该如何添加一个 Skill 让你下次能用上。
```

（期望：先尝试 `load_skill` 或根据错误信息判断；未安装 S0 时不应瞎编 Skill 正文。）

### Z7 — 看板与依赖（复杂一点的任务分解）

```text
我想做两件事：A）整理 TEST.md 的目录结构加一个小节标题；B）在 TODO.md 里加一条「已完成 Z7 测试」的记录。两件事可以并行思考，但 B 依赖 A 的文件名别写错。请你一次性推进到完成。
```

（期望：可能 `task_create` 两条带依赖，或 `todo_write` 跟踪；至少多次文件读写与一致命名。）

### Z8 — 上下文变长时的自省（压缩）

```text
请先简要复述从对话开始到现在用户提过的所有测试主题关键词（不少于 8 个词），然后如果上下文已经偏长，请你主动采取你认为合适的节省 token 的方式，再继续用一句话总结 ycy 的定位。
```

（期望：可能调用 `compress` 或依赖内置 auto_compact；考察是否有「节省 token」意识。）

---

### 隐性用例检查清单（可选）

| 编号 | 考察点 |
|------|--------|
| Z1 | 读文件而非臆测 |
| Z2 | 进度跟踪 + 实际改 README |
| Z3 | 子代理或等价隔离探查 |
| Z4 | 队友/消息/任务板联动思路 |
| Z5 | 后台执行 |
| Z6 | Skill 探测与诚实响应 |
| Z7 | 多步一致性与依赖 |
| Z8 | 压缩 / 上下文管理 |

---

使用说明：测试完成后可删除 `_ycy_test.txt` 及测试用看板任务文件，避免污染仓库。
