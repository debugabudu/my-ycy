import os


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


TOKEN_THRESHOLD = _env_int("YCY_TOKEN_THRESHOLD", 100000)
POLL_INTERVAL = _env_int("YCY_POLL_INTERVAL", 5)
IDLE_TIMEOUT = _env_int("YCY_IDLE_TIMEOUT", 60)
SUBAGENT_MAX_TURNS_DEFAULT = _env_int("YCY_SUBAGENT_MAX_TURNS", 30)
TEAMMATE_MAX_TOOL_ROUNDS_PER_CYCLE = _env_int("YCY_TEAMMATE_MAX_TOOL_ROUNDS", 50)

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# 消息总线 MessageBus 里的发送方/收件箱 id（与 loop、protocols 一致）
LEAD_ACTOR_ID = "lead"
# 子代理实例 id 前缀；每次 task 调用应使用独立 actor id
SUBAGENT_ACTOR_PREFIX = "subagent"
