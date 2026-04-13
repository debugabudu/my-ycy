from pathlib import Path

from ycy.agent.profiles.models import AgentProfile


def resolve_subagent_system(profile: AgentProfile | None, workdir: Path) -> str | None:
    if profile is None:
        return None
    if profile.use_body_as_system and profile.body.strip():
        return profile.body.strip()
    if profile.system_template:
        return profile.system_template.format(workdir=workdir)
    return None


def resolve_teammate_system(
    profile: AgentProfile | None,
    *,
    name: str,
    role: str,
    team_name: str,
    workdir: Path,
) -> str:
    default = (
        f"你是队友「{name}」，角色：{role}，所属团队：{team_name}。工作目录：{workdir}。\n"
        "请使用简体中文回复。通过 send_message、read_inbox、broadcast 与团队协调。\n"
        "暂停当前工作时调用 idle；需要占用看板任务时用 claim_task。\n"
        "仅在个人配置允许且工具集中包含 claim_task 时，空闲阶段才可能自动认领待办任务。"
    )
    if profile is None:
        return default
    if profile.use_body_as_system and profile.body.strip():
        return profile.body.strip()
    if profile.system_template:
        return profile.system_template.format(
            name=name, role=role, team_name=team_name, workdir=workdir
        )
    return default
