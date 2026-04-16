import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"
SKILLS_DIR = WORKDIR / "skills"
AGENTS_DIR = WORKDIR / "agents"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TRACE_DIR = WORKDIR / ".trace"
SESSIONS_DIR = WORKDIR / ".sessions"
MEMORY_DIR = WORKDIR / ".memory"
MEMORY_DB = MEMORY_DIR / "memory.db"
VECTOR_DB = MEMORY_DIR / "vector.db"
