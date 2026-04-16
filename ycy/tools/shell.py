import os
import shlex
import subprocess

from ycy.config import WORKDIR


def _validate_command(command: str) -> tuple[bool, str]:
    cmd = (command or "").strip()
    if not cmd:
        return False, "空命令"
    low = cmd.lower()
    dangerous_patterns = [
        "rm -rf /",
        ":(){ :|:& };:",
        "sudo ",
        " shutdown",
        " reboot",
        "> /dev/",
        "mkfs",
        "dd if=",
    ]
    if any(p in low for p in dangerous_patterns):
        return False, "命中危险命令规则"
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return False, "命令解析失败"
    if not tokens:
        return False, "空命令"
    # 可选前缀白名单：YCY_BASH_ALLOW_PREFIX="git,pytest,python,python3,ls"
    allow_prefix = [
        p.strip() for p in os.getenv("YCY_BASH_ALLOW_PREFIX", "").split(",") if p.strip()
    ]
    if allow_prefix and tokens[0] not in allow_prefix:
        return False, f"命令前缀不在白名单：{tokens[0]}"
    return True, ""


def run_bash(command: str) -> str:
    ok, reason = _validate_command(command)
    if not ok:
        return f'{{"ok": false, "reason": "{reason}"}}'
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "（无输出）"
    except subprocess.TimeoutExpired:
        return "错误：命令超时（120 秒）"
