from pathlib import Path

from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.constants import LEAD_ACTOR_ID
from ycy.skills.loader import SkillLoader

# 无 AGENT.md profile、仅内置工具集时的子 agent 系统提示
BUILTIN_SUBAGENT_SYSTEM = (
    "你是生命周期较短的编码子代理，固定配备工作区工具（shell、读/写/改文件）。"
    "请用工具查看仓库并回答问题，优先依据命令与文件内容，少猜测。"
    "最终回复请简洁；与用户沟通时使用简体中文。"
)

# 若 Skill/Agent 正文为英文，仍用中文向用户说明结论。


def build_system_prompt(
    workdir: Path, skills: SkillLoader, agents: AgentProfileLoader
) -> str:
    return f"""你是主会话中的首席编码助手（lead），主要工作目录：{workdir}。

请使用简体中文与用户交流；阅读英文 Skill/Agent 正文时，仍用中文作答。

任务组织：多步骤、需持久跟踪的工作请优先使用 task_create、task_update、task_list（看板任务）。
会话内简短清单请用 todo_write（与看板任务区分）。

子代理：task 工具必须带 profile=（agents 下配置 id），用于上下文隔离与工具边界；无特殊需求可用 subagent-default。
队友：spawn_teammate 必须带 profile=（kind 含 teammate 的专家配置），成本较高，仅多专家协作时使用；通用模板可用 teammate-default。

按需加载：load_skill 获取打包知识；需要完整配置正文时用 load_agent_profile。

协作：你在消息总线上的身份 id 为「{LEAD_ACTOR_ID}」；队友使用各自 spawn 时的 name。
send_message、read_inbox、broadcast 会自动使用当前身份，无需改工具名。

Agent 配置摘要：
{agents.descriptions()}

Skill 摘要：
{skills.descriptions()}"""
