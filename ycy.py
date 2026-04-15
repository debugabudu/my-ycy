import argparse
import json
import logging

from ycy.agent.loop import agent_loop
from ycy.agent.tool_runner import summarize_text_response
from ycy.constants import LEAD_ACTOR_ID
from ycy.context.compact import auto_compact
from ycy.observability.logging_setup import setup_logging
from ycy.observability.tracing import init_session
from ycy.runtime.env_check import verify_runtime
from ycy.runtime.startup_policy import apply_startup_policy

_log = logging.getLogger("ycy.main")


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="ycy CLI")
    parser.add_argument(
        "--startup-policy",
        choices=("fresh", "resume"),
        default="fresh",
        help="fresh: 启动前清空任务与团队状态；resume: 保留上次状态",
    )
    args = parser.parse_args()
    from ycy import config

    verify_runtime(
        workdir=config.WORKDIR,
        trace_dir=config.TRACE_DIR,
        transcript_dir=config.TRANSCRIPT_DIR,
    )
    apply_startup_policy(
        args.startup_policy,
        tasks_dir=config.TASKS_DIR,
        team_dir=config.TEAM_DIR,
        inbox_dir=config.INBOX_DIR,
    )
    from ycy import container

    init_session(config.TRACE_DIR)
    _log.info(
        "Model=%s workdir=%s startup_policy=%s",
        config.MODEL,
        config.WORKDIR,
        args.startup_policy,
    )

    history = []
    while True:
        try:
            query = input("\033[36mycy >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/compact":
            if history:
                _log.info("Manual compact via /compact")
                history[:] = auto_compact(history)
            continue
        if query.strip() == "/tasks":
            print(container.TASK_MGR.list_all())
            continue
        if query.strip() == "/team":
            print(container.TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(
                json.dumps(
                    container.BUS.read_inbox(LEAD_ACTOR_ID),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            continue
        history.append({"role": "user", "content": query})
        final_resp = agent_loop(history)
        print(summarize_text_response(final_resp, empty="（模型未返回文本）"))
        print()


if __name__ == "__main__":
    main()
