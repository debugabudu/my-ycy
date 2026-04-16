from ycy.constants import VALID_MSG_TYPES

TOOLS = [
    {
        "name": "current_time",
        "description": "获取当前本地时间（含时区、ISO 时间、星期与 Unix 时间戳）。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "web_search",
        "description": "使用智谱 Web Search API 进行联网检索并返回结构化结果。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或问题"},
                "count": {"type": "integer", "description": "返回结果数（1-50，默认 8）"},
                "search_engine": {
                    "type": "string",
                    "description": "搜索引擎档位（如 search_std/search_pro，默认 search_std）",
                },
                "search_domain_filter": {"type": "string", "description": "可选，限定检索域名"},
                "search_recency_filter": {
                    "type": "string",
                    "description": "可选，时间范围过滤（默认 noLimit）",
                },
                "content_size": {
                    "type": "string",
                    "description": "摘要长度档位（low/medium/high，默认 medium）",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "bash",
        "description": "在 shell 中执行一条命令（工作目录一般为当前项目）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "读取指定路径文件的文本内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "limit": {"type": "integer", "description": "可选，最多读取行数/长度限制（由实现决定）"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "将内容写入文件（覆盖写入）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件完整内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "在文件中将一段文本精确替换为另一段（需与原文完全一致匹配）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_text": {"type": "string", "description": "要被替换的原文"},
                "new_text": {"type": "string", "description": "替换后的新文本"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "restore_file_backup",
        "description": "使用备份文件恢复目标文件内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目标文件路径"},
                "backup_path": {"type": "string", "description": "备份文件路径"},
            },
            "required": ["path", "backup_path"],
        },
    },
    {
        "name": "todo_write",
        "description": "更新本会话内的简短待办列表（非任务看板上的持久化任务）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "待办项列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "待办描述"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "状态：pending / in_progress / completed",
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "可选。进行中时用于列表右侧简短状态（如「正在跑测试」）；省略则与 content 相同。",
                            },
                        },
                        "required": ["content", "status"],
                    },
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "task",
        "description": (
            "启动子代理：独立上下文与工具边界，适合隔离推理、权限裁剪或并行子任务。"
            "必须通过 profile 指定 agents 下某套 AGENT.md（如 subagent-default、explore）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "交给子代理完成的任务说明"},
                "profile": {
                    "type": "string",
                    "description": (
                        "必填。子代理配置 id（agents/<id>/AGENT.md）。"
                        "无特殊需求可用 subagent-default（四类工作区工具）。"
                    ),
                },
            },
            "required": ["prompt", "profile"],
        },
    },
    {
        "name": "load_skill",
        "description": "按名称加载已打包的 Skill 正文（领域知识/流程说明）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill 名称（与 skills 目录中定义一致）"},
                "mode": {
                    "type": "string",
                    "enum": ["full", "summary"],
                    "description": "加载模式：full 返回全文，summary 返回摘要",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "skill_draft_from_chat",
        "description": "从最近会话自动生成 Skill 草稿到 skills/<name>/SKILL.md。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill id"},
                "focus": {"type": "string", "description": "可选，草稿聚焦主题"},
                "n_rounds": {"type": "integer", "description": "提取最近轮次，默认 6"},
                "overwrite": {"type": "boolean", "description": "已存在时是否覆盖"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "skill_index_memory",
        "description": "将 Skill 关键片段写入长期记忆与向量索引。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill 名称"},
                "namespace": {"type": "string", "description": "向量命名空间，默认 skills"},
                "max_chunks": {"type": "integer", "description": "最多索引片段数，默认 8"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "load_agent_profile",
        "description": "按 id 加载完整 Agent 配置（元数据 + 正文），用于系统摘要不足以决策时。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent 配置 id"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "compress",
        "description": "手动触发对当前对话上下文的压缩摘要（节省 token）。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "memory_append",
        "description": "向长期记忆库追加结构化记忆条目（显式写入）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "记忆正文"},
                "summary": {"type": "string", "description": "可选摘要"},
                "source": {"type": "string", "description": "来源，如 user_note/session/tool_result"},
                "run_id": {"type": "string", "description": "来源会话 run_id（可选）"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "anchors": {"type": "array", "items": {"type": "string"}},
                "importance": {"type": "integer", "description": "1-5，默认 3"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "memory_search",
        "description": "检索长期记忆，支持按关键词、标签、时间窗口过滤。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "from_time": {"type": "string", "description": "ISO 时间下限"},
                "to_time": {"type": "string", "description": "ISO 时间上限"},
                "limit": {"type": "integer", "description": "返回条数，默认 10"},
            },
        },
    },
    {
        "name": "memory_compact",
        "description": "压缩长期记忆条目，默认保护带 anchors 的条目。",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {"type": "integer", "description": "最大保留条数，默认 500"},
                "preserve_anchors": {"type": "boolean", "description": "是否保留带 anchors 的条目"},
            },
        },
    },
    {
        "name": "vector_index",
        "description": "向向量索引写入文本，或为指定目录建立分块索引。",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "索引命名空间，默认 notes"},
                "path": {"type": "string", "description": "可选，目录路径（批量建索引）"},
                "text": {"type": "string", "description": "可选，直接写入单条文本"},
                "ref_type": {"type": "string", "description": "text 模式下的引用类型"},
                "ref_id": {"type": "string", "description": "text 模式下的引用 id"},
                "meta": {"type": "object", "description": "text 模式下附加元数据"},
            },
        },
    },
    {
        "name": "vector_search",
        "description": "在指定 namespace 中做向量近似检索并返回引用片段。",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "索引命名空间"},
                "query": {"type": "string", "description": "检索问题"},
                "top_k": {"type": "integer", "description": "返回条数，默认 5"},
                "min_score": {"type": "number", "description": "最小相关度阈值，默认 0.05"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "background_run",
        "description": "在后台线程执行 shell 命令，避免长时间阻塞主循环。",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "命令"},
                "timeout": {"type": "integer", "description": "超时秒数，默认 120"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "check_background",
        "description": "查询后台任务的执行状态与输出。",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "background_run 返回的任务 id"},
            },
        },
    },
    {
        "name": "task_create",
        "description": "在看板上创建持久化任务（多步骤协作优先用看板任务）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "可选，详细说明"},
            },
            "required": ["subject"],
        },
    },
    {
        "name": "task_get",
        "description": "按 id 查看单个看板任务的详情（JSON）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "任务数字 id"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_update",
        "description": "更新看板任务状态或依赖关系（阻塞/被阻塞）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "任务 id"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "deleted"],
                    "description": "状态",
                },
                "add_blocked_by": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "新增「被哪些任务阻塞」",
                },
                "add_blocks": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "新增「阻塞哪些任务」",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_list",
        "description": "列出当前看板上所有任务摘要。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "spawn_teammate",
        "description": (
            "启动长期运行的专家队友线程（独立循环、收件箱与工具集）。"
            "成本较高，仅在需要多专家协作或持续并行时使用；简单隔离请用 task + subagent profile。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "队友名称（消息总线中的身份 id）"},
                "role": {"type": "string", "description": "角色"},
                "prompt": {"type": "string", "description": "初始任务/上下文说明"},
                "profile": {
                    "type": "string",
                    "description": (
                        "必填。专家配置 id（agents/<id>/AGENT.md，kind 为 teammate 或 both）。"
                        "通用模板可用 teammate-default。"
                    ),
                },
            },
            "required": ["name", "role", "prompt", "profile"],
        },
    },
    {
        "name": "list_teammates",
        "description": "列出当前团队配置中的队友及其状态。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_message",
        "description": "向指定 id 的参与者发送一条消息（发件人为当前 agent 身份）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "收件人 id（如 lead 或队友 name）"},
                "content": {"type": "string", "description": "消息正文"},
                "msg_type": {
                    "type": "string",
                    "enum": list(VALID_MSG_TYPES),
                    "description": "消息类型",
                },
            },
            "required": ["to", "content"],
        },
    },
    {
        "name": "read_inbox",
        "description": "读取并清空当前身份对应的收件箱（主 agent 为 lead，队友为各自 name，子代理为 subagent）。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "broadcast",
        "description": "向除自己以外的所有队友广播一条消息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "广播内容"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "shutdown_request",
        "description": "请求指定队友进入关闭流程（通过消息总线发送关机类通知）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "teammate": {"type": "string", "description": "目标队友 name"},
            },
            "required": ["teammate"],
        },
    },
    {
        "name": "plan_approval",
        "description": "对队友发起的计划审批请求进行通过或驳回。",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "计划请求 id"},
                "approve": {"type": "boolean", "description": "是否通过"},
                "feedback": {"type": "string", "description": "可选反馈意见"},
            },
            "required": ["request_id", "approve"],
        },
    },
    {
        "name": "idle",
        "description": "声明进入空闲/等待状态（队友循环中用于结束当前工作片段）。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "claim_task",
        "description": "在看板上认领（占用）指定 id 的任务，归属为当前身份。",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "任务 id"},
            },
            "required": ["task_id"],
        },
    },
]
