import argparse
import json
import logging
import sys

from ycy.agent.loop import agent_loop
from ycy.agent.tool_runner import summarize_text_response
from ycy.constants import LEAD_ACTOR_ID
from ycy.context.compact import auto_compact
from ycy.memory_session import append_turn, create_new_session, load_session, save_session
from ycy.observability.logging_setup import setup_logging
from ycy.observability.tracing import init_session
from ycy.runtime.env_check import verify_runtime
from ycy.runtime.startup_policy import apply_startup_policy
from ycy.skills.scaffold import init_skill_file

_log = logging.getLogger("ycy.main")


def main():
    setup_logging()
    if len(sys.argv) >= 4 and sys.argv[1] == "init" and sys.argv[2] == "skill":
        from ycy import config

        skill_id = sys.argv[3].strip()
        if not skill_id:
            print("错误：skill id 不能为空")
            return
        try:
            path = init_skill_file(config.SKILLS_DIR, skill_id)
            print(f"已创建 Skill 脚手架：{path}")
        except FileExistsError as e:
            print(str(e))
        return

    parser = argparse.ArgumentParser(description="ycy CLI")
    parser.add_argument(
        "--startup-policy",
        choices=("fresh", "resume"),
        default="fresh",
        help="fresh: 启动前清空任务与团队状态；resume: 保留上次状态",
    )
    parser.add_argument(
        "--resume-session",
        metavar="SESSION",
        help="从历史会话续聊：SESSION 可为 latest、会话文件名或 session_id 前缀。",
    )
    args = parser.parse_args()
    from ycy import config

    verify_runtime(
        workdir=config.WORKDIR,
        trace_dir=config.TRACE_DIR,
        transcript_dir=config.TRANSCRIPT_DIR,
        sessions_dir=config.SESSIONS_DIR,
        memory_dir=config.MEMORY_DIR,
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

    if args.resume_session:
        try:
            sess = load_session(args.resume_session)
            history = [{"role": t.role, "content": t.content} for t in sess.history]
            _log.info(
                "Resumed session session_id=%s turns=%d",
                sess.meta.session_id,
                len(sess.history),
            )
        except FileNotFoundError as e:
            _log.warning("%s，启动新会话。", e)
            sess = create_new_session()
            history = []
    else:
        sess = create_new_session()
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
        append_turn(sess, "user", query)
        final_resp = agent_loop(history)
        print(summarize_text_response(final_resp, empty="（模型未返回文本）"))
        # agent_loop 已就地更新 history，此处根据 history 追加最新一条 assistant 文本到会话文件
        if history and history[-1]["role"] == "assistant":
            append_turn(sess, "assistant", history[-1]["content"])
        save_session(sess)
        print()


if __name__ == "__main__":
    main()
