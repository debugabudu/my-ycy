# ycy

面向本地工作区的 **编码 Agent 运行时**：在 REPL 中与模型多轮对话，通过 **工具** 读写文件、执行命令、管理看板任务与团队消息，并支持 **子代理（隔离上下文）** 与 **长期运行的队友线程**。

## 1. 项目说明

### 1.1 架构概览

- **入口**：`ycy.py` 启动交互循环，用户输入进入 `agent_loop`。
- **主 Agent（lead）**：单会话、全量工具列表（`ycy/tools/definitions.py` 中的 `TOOLS`），系统提示由 `build_system_prompt` 生成（`ycy/agent/prompts.py`）。
- **工具执行**：`ycy/container.py` 中 `TOOL_HANDLERS = make_tool_handlers(...)`，与 `TOOLS` 一一对应；主循环用 `dispatch_tool_use_blocks` 分发。
- **子代理（subagent）**：由主 Agent 调用 `task` 工具触发 `run_subagent`（`ycy/agent/subagent.py`），**必须**指定 `agents/<profile>/AGENT.md` 的 profile id；独立 `messages` 与工具子集。
- **队友（teammate）**：由 `spawn_teammate` 在后台线程中运行（`ycy/team/teammate.py`），**必须**指定 `kind` 含 `teammate` 或 `both` 的 profile；通过 `MessageBus`（`.team/inbox/*.jsonl`）与 lead 通信。
- **配置与数据目录**（相对当前工作目录，见 `ycy/config.py`）：
  - `agents/`：Agent profile（`AGENT.md`）
  - `skills/`：Skill（`SKILL.md`）
  - `.tasks/`：持久化看板任务 JSON
  - `.team/`：团队配置与收件箱
  - `.sessions/`：短期会话记忆（按会话文件保存 history）
  - `.memory/`：长期记忆与向量索引（SQLite）
  - `.trace/`：可选 JSONL 轨迹（`YCY_TRACE`）
  - `.transcripts/`：预留

### 1.2 主 Agent（lead）具备的能力

主 Agent 可使用 `TOOLS` 中的全部工具（名称与 schema 以 `ycy/tools/definitions.py` 为准），语义上可分为：

| 类别 | 工具名 | 说明 |
|------|--------|------|
| 联网检索 | `web_search` | 调用智谱 Web Search API，返回结构化搜索结果 JSON（需 `ZAI_API_KEY`） |
| 工作区 | `bash`, `read_file`, `write_file`, `edit_file` | Shell 与文件读写；路径受工作区约束（见 `filesystem.safe_path`） |
| 会话待办 | `todo_write` | 本会话内短清单（非 `.tasks` 看板） |
| 子代理 | `task` | `prompt` + **必填** `profile`；隔离上下文与子集工具 |
| 知识 | `load_skill`, `load_agent_profile` | 按需加载 Skill 正文或完整 Agent 配置 |
| 上下文 | `compress` | 请求对对话做压缩（与 token 阈值、`auto_compact` 协同） |
| 后台命令 | `background_run`, `check_background` | 异步 shell，结果经队列注入主循环 |
| 看板任务 | `task_create`, `task_get`, `task_update`, `task_list`, `claim_task` | `.tasks` 下持久任务；`claim_task` 将任务归属为当前身份（lead 为 `lead`） |
| 团队 | `spawn_teammate`, `list_teammates`, `send_message`, `read_inbox`, `broadcast`, `shutdown_request`, `plan_approval` | 启停队友、列表、消息总线；主身份 id 为 **`lead`**（`LEAD_ACTOR_ID`） |
| 队友专用（对 lead 多为无操作或提示） | `idle` | lead 调用时返回说明性文案；队友用于结束工作片段 |
| 记忆（长期） | `memory_append`, `memory_search`, `memory_compact` | 显式写入/检索/压缩长期记忆，支持 tags、时间窗口、anchors 保护 |
| 记忆（向量） | `vector_index`, `vector_search` | 对文本或目录建索引；按 namespace 检索语义近邻片段 |
| Skill 沉淀 | `skill_draft_from_chat`, `skill_index_memory` | 从最近对话生成 Skill 草稿；将 Skill 关键片段写入记忆与向量索引 |

主循环还会：**自动注入** lead 的 `read_inbox` 内容、后台任务完成通知；超过 `YCY_TOKEN_THRESHOLD` 时触发 `auto_compact`；若存在未完成 todo 且多轮未调用 `todo_write`，会插入提醒（见 `ycy/agent/loop.py`）。

### 1.3 子代理（subagent）的能力

- 工具集 = **`AGENT.md` 中 `tools` 列表**（经 `filter_unknown_tools` 过滤，仅保留 `definitions` 中存在的名字）**并上** 固定 **`load_skill`**（`ycy/agent/bundles.py` 中 `SUBAGENT_ALWAYS_TOOLS`）。
- 若 profile 中无有效工具名，会回退到「四类工作区工具 + `load_skill`」。
- 消息总线身份为 **`subagent`**（`SUBAGENT_ACTOR_ID`）；**并行多个 `task` 时共用一个收件箱**，需注意串扰。
- 系统提示：`system_template` / `use_body_as_system` 或兜底 `BUILTIN_SUBAGENT_SYSTEM`。

### 1.4 队友（teammate）的能力

- 工具集 = profile 声明的 `tools` **并上** `TEAMMATE_BASE_TOOLS`（协作类 + 工作区四类 + `load_skill`），见 `ycy/agent/bundles.py`。
- **必须**提供 profile（如 `teammate-default`）；`spawn` 前会校验 `allows_teammate()`。
- 身份为 spawn 时指定的 **`name`**（每人独立 `inbox` 文件）。
- 空闲阶段是否自动认领看板任务：由 profile 的 **`auto_claim_tasks`** 与 bundle 中是否含 **`claim_task`** 共同决定。

---

## 2. 使用方式与注意事项

### 2.1 环境依赖

- Python 3；需安装 **`anthropic`** SDK 与 **`python-dotenv`**（见 `ycy/config.py`）。
- 环境变量：
  - **`MODEL_ID`**：模型名称（必填，未设置时启动可能失败）。
  - **`ZAI_API_KEY`**（可选）：启用 `web_search` 工具时必填（智谱/ZAI 的 API Key）。
  - **`ANTHROPIC_BASE_URL`**（可选）：兼容 Anthropic API 的网关（如智谱等）；若设置，会清除 `ANTHROPIC_AUTH_TOKEN` 以适配部分网关认证方式，请按你的服务商文档配置密钥环境变量。
- 在项目根目录准备 **`.env`**（`load_dotenv`）写入上述变量。

### 2.2 启动

```bash
cd /path/to/my-ycy
python ycy.py
```

在 `ycy >>` 提示符下输入自然语言；输入 `q` / `exit` / 空行退出。

### 2.3 REPL 内建命令（不经过模型）

| 输入 | 作用 |
|------|------|
| `/compact` | 对当前 `history` 执行 `auto_compact` |
| `/tasks` | 打印看板任务列表 |
| `/team` | 打印队友列表 |
| `/inbox` | 读取并清空 lead 收件箱（调试） |

### 2.4 注意事项

1. **工作目录**：`WORKDIR = Path.cwd()`，文件与 shell 均相对**启动 ycy 时的当前目录**；请在目标仓库根目录启动。
2. **Agent / Skill 热加载**：`AGENTS`、`SKILLS` 在 **import `container` 时** 扫描磁盘；修改 `agents/`、`skills/` 后需**重启进程**才能生效。
3. **`task` 与 `spawn_teammate` 必须带 `profile`**：子代理用 `subagent-default` 等；队友用 `teammate-default` 或自建 `kind: teammate` / `both` 的 profile。
4. **工具名唯一事实源**：`ycy/tools/definitions.py`；`AGENT.md` 的 `tools:` 须与其中 **`name` 字段**一致（英文 snake_case 等），未知名字会在加载时被丢弃并打日志。
5. **新增工具** 必须同时改 `definitions`、`make_tool_handlers`（`ycy/tools/handlers.py`），否则 profile 无法真正执行。
6. **安全**：`bash` 有简单危险命令拦截；仍应对不可信代码与生产环境谨慎使用。
7. **轨迹**：默认 `YCY_TRACE` 非 `0/false/no` 时写 `.trace/run_*.jsonl`；关闭可设 `YCY_TRACE=0`。
8. **可调常量**：`YCY_TOKEN_THRESHOLD`、`YCY_SUBAGENT_MAX_TURNS`、`YCY_IDLE_TIMEOUT`、`YCY_POLL_INTERVAL` 等见 `ycy/constants.py`。
9. **联网搜索**：`web_search` 依赖 `zai-sdk` 与环境变量 `ZAI_API_KEY`；可选参数包含 `count`、`search_engine`、`search_domain_filter`、`search_recency_filter`、`content_size`。

### 2.5 记忆能力使用说明（1.1）

#### A. 短期会话记忆（`.sessions/`）

- 启动新会话：默认行为（不带 `--resume-session`）。
- 续聊历史会话：
  - `python ycy.py --resume-session latest`（最近一次）
  - `python ycy.py --resume-session <session_id前缀>`
  - `python ycy.py --resume-session <会话文件名>`
- 每轮对话后会自动落盘；会话文件包含 `meta + history`。

#### B. 长期记忆（显式写入，`.memory/memory.db`）

- 写入：`memory_append`
  - 最少参数：`text`
  - 建议同时给：`tags`、`anchors`、`importance`
- 检索：`memory_search`
  - 支持 `query`（关键词）、`tags`（标签过滤）、`from_time/to_time`（ISO 时间窗口）、`limit`
- 压缩：`memory_compact`
  - `max_entries` 控制保留上限
  - `preserve_anchors=true` 时默认保护含锚点条目（人名、长期目标、禁忌等）

#### C. 向量检索（`.memory/vector.db`）

- 建索引：`vector_index`
  - 目录模式：传 `path`（会对 `.md/.txt` 分块索引）
  - 文本模式：传 `text`（写入单条）
  - 通过 `namespace` 隔离不同知识域（如 `notes`、`memories`）
- 检索：`vector_search`
  - 关键参数：`namespace`、`query`、`top_k`、`min_score`
  - 返回内容包含片段文本与相关度分数，适合带引用回答

#### D. 推荐使用流程（实践）

1. 对“长期稳定信息”调用 `memory_append`（例如偏好、长期目标、禁忌）。
2. 回忆历史事实时先 `memory_search`；不足再 `vector_search`。
3. 用户指定目录（笔记/纪要）先 `vector_index`，之后复用 `namespace` 检索。
4. 定期 `memory_compact`，并保持 `anchors` 完整，避免关键偏好被清掉。

### 2.6 Skill 快速沉淀（1.3）

#### A. 一键生成 Skill 草稿
- 工具：`skill_draft_from_chat`
- 作用：从最近会话提炼内容并写入 `skills/<name>/SKILL.md`
- 常用参数：
  - `name`：Skill id（必填）
  - `focus`：可选聚焦主题
  - `n_rounds`：回看最近轮次（默认 6）
  - `overwrite`：已存在是否覆盖（默认 false）

#### B. Skill 版本与摘要
- `SKILL.md` frontmatter 建议包含：
  - `version`（如 `0.1.0`）
  - `updated`（ISO 日期）
  - `summary`（一行摘要）
- `load_skill` 支持：
  - `mode=summary`：先返回摘要
  - `mode=full`：返回全文（默认）

#### C. 脚手架命令
- 命令：`python ycy.py init skill <id>`
- 作用：生成标准 `skills/<id>/SKILL.md`（含 frontmatter 与示例段落）

#### D. 与记忆联动
- 工具：`skill_index_memory`
- 作用：把 Skill 关键片段写入：
  - 长期记忆库（带 `skill:<name>` 标签）
  - 向量索引（默认 `namespace=skills`）

---

## 3. 新增 / 修改 / 删除：工具、Skill、Agent

### 3.1 工具（Tools）

**事实源**：`ycy/tools/definitions.py` 的 `TOOLS` 列表（每项含 `name`、`description`、`input_schema`）。

**新增**

1. 在 `TOOLS` 中追加一项，**`name` 全局唯一**。
2. 在 `ycy/tools/handlers.py` 的 `make_tool_handlers` 返回的字典中增加同名键，值为可调用实现（通常 `lambda **kw: ...`）。
3. 若实现放在新模块，在 `handlers` 中导入并调用；保持参数与 schema 一致。
4. **无需**改 `catalog.py`（其从 `TOOLS` 自动生成 `TOOL_SPEC_BY_NAME`）。

**修改**

1. 改 `definitions` 中对应项的 `description` / `input_schema`（影响模型可见说明）。
2. 同步改 `handlers` 中实现与参数解析。

**删除**

1. 从 `TOOLS` 移除该项。
2. 从 `make_tool_handlers` 移除对应键。
3. 全局搜索该工具名，更新所有 `agents/**/AGENT.md` 的 `tools:` 行，避免加载时被 `filter_unknown_tools` 静默丢弃。

### 3.2 Skill

**约定**：`skills/` 下任意子目录中的 **`SKILL.md`**；支持 YAML frontmatter（`---` 包裹）。

**新增**

1. 创建例如 `skills/<id>/SKILL.md`。
2. 首段 frontmatter 建议包含：`name`（可选，默认用目录名）、`description`（用于系统摘要列表）。
3. 正文为 Markdown，由 `load_skill` 整体注入对话。

**修改**

直接编辑对应 `SKILL.md`；**重启 ycy** 后生效。

**删除**

删除对应目录或 `SKILL.md`；重启进程。

### 3.3 Agent（Profile）

**约定**：`agents/<id>/AGENT.md`，**必须**含 frontmatter。解析规则见 `ycy/content/frontmatter.py` 与 `parse_agent_meta_lines`（`tools` 为逗号分隔列表）。

**常用 frontmatter 字段**

| 字段 | 说明 |
|------|------|
| `name` | 配置 id，默认目录名 |
| `description` | 摘要 |
| `kind` | `subagent` / `teammate` / `both` |
| `tools` | 逗号分隔工具名，须存在于 `definitions` |
| `max_turns` | 子代理最大轮次（整数） |
| `system_template` | 系统提示模板，可用 `{workdir}`；队友还可 `{name},{role},{team_name}` |
| `use_body_as_system` | `true` 时用正文作系统提示 |
| `auto_claim_tasks` | 队友空闲是否自动抢单（默认 true） |

**新增**

1. 新建 `agents/<profile_id>/AGENT.md`。
2. 按角色设置 `kind` 与 `tools`。
3. 子代理供 `task` 的 `profile=<profile_id>`；队友供 `spawn_teammate` 的 `profile=<profile_id>`。

**修改**

编辑文件；重启进程。

**删除**

删除目录；检查是否仍有 prompt 或脚本引用该 id。

---

## 4. 仓库内建 Profile

- `agents/subagent-default/`：子代理默认配方（工作区工具 + `load_skill`）。
- `agents/teammate-default/`：队友通用模板（`kind: teammate`）。

建议保留二者作为文档化入口；复杂场景可复制目录改名后改 `name`/`tools`/`kind`。

---

## 5. 相关文件索引

| 模块 | 路径 |
|------|------|
| 工具定义 | `ycy/tools/definitions.py` |
| 工具实现 | `ycy/tools/handlers.py` |
| 主循环 | `ycy/agent/loop.py` |
| 系统提示 | `ycy/agent/prompts.py` |
| 子代理 | `ycy/agent/subagent.py` |
| Bundle 合并规则 | `ycy/agent/bundles.py` |
| Agent 加载 | `ycy/agent/profiles/loader.py` |
| Skill 加载 | `ycy/skills/loader.py` |
| 配置 | `ycy/config.py` |
| 全局单例 | `ycy/container.py` |