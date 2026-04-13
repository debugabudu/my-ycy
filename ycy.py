import json
import logging

from ycy.agent.loop import agent_loop
from ycy.constants import LEAD_ACTOR_ID
from ycy.context.compact import auto_compact
from ycy.observability.logging_setup import setup_logging
from ycy.observability.tracing import init_session
from ycy.runtime.env_check import verify_runtime

_log = logging.getLogger("ycy.main")


def main():
    setup_logging()
    from ycy import config
    from ycy import container

    verify_runtime(
        workdir=config.WORKDIR,
        trace_dir=config.TRACE_DIR,
        transcript_dir=config.TRANSCRIPT_DIR,
    )
    init_session(config.TRACE_DIR)
    _log.info("Model=%s workdir=%s", config.MODEL, config.WORKDIR)

    history = []
    while True:
        try:
            query = input("\033[36ycy >> \033[0m")
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
            print(json.dumps(container.BUS.read_inbox(LEAD_ACTOR_ID), indent=2))
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        print()


if __name__ == "__main__":
    main()
