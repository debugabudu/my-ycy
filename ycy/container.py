from ycy.agent.prompts import build_system_prompt
from ycy.agent.profiles.loader import AgentProfileLoader
from ycy.config import AGENTS_DIR, SKILLS_DIR, WORKDIR
from ycy.runtime.background_manager import BackgroundManager
from ycy.skills.loader import SkillLoader
from ycy.tasks.board import TaskManager
from ycy.tasks.todos import TodoManager
from ycy.team.bus import MessageBus
from ycy.team.teammate import TeammateManager
from ycy.tools.definitions import TOOLS
from ycy.tools.handlers import make_tool_handlers

TODO = TodoManager()
SKILLS = SkillLoader(SKILLS_DIR)
AGENTS = AgentProfileLoader(AGENTS_DIR)
TASK_MGR = TaskManager()
BG = BackgroundManager()
BUS = MessageBus()
TEAM = TeammateManager(
    BUS, TASK_MGR, profile_loader=AGENTS, skills=SKILLS, todo=TODO, bg=BG
)

TOOL_HANDLERS = make_tool_handlers(TODO, SKILLS, TASK_MGR, BG, BUS, TEAM, AGENTS)
SYSTEM = build_system_prompt(WORKDIR, SKILLS, AGENTS)

__all__ = [
    "AGENTS",
    "BG",
    "BUS",
    "SKILLS",
    "SYSTEM",
    "TASK_MGR",
    "TEAM",
    "TODO",
    "TOOL_HANDLERS",
    "TOOLS",
]
