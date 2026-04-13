"""启动时环境与健康检查（目录可写、关键变量）。"""

import logging
import os
from pathlib import Path

_log = logging.getLogger("ycy.env")


def ensure_dir(path: Path, *, label: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _log.warning("Cannot create %s %s: %s", label, path, e)


def verify_runtime(*, workdir: Path, trace_dir: Path, transcript_dir: Path) -> None:
    """尽力创建运行时目录；失败仅打日志。"""
    ensure_dir(workdir, label="workdir")
    ensure_dir(trace_dir, label="trace")
    ensure_dir(transcript_dir, label="transcript")
    if not os.environ.get("MODEL_ID"):
        _log.warning("MODEL_ID is not set; import of config may already have failed")
