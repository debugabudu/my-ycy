import json
import os
from typing import Any


def _to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, tuple):
        return [_to_plain(v) for v in value]
    if isinstance(value, set):
        return [_to_plain(v) for v in value]
    if hasattr(value, "to_dict"):
        try:
            return _to_plain(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_plain(vars(value))
        except Exception:
            pass
    return value


def run_web_search(
    query: str,
    *,
    count: int = 10,
    search_engine: str = "search_pro",
    search_domain_filter: str | None = None,
    search_recency_filter: str = "noLimit",
    content_size: str = "medium",
) -> str:
    q = (query or "").strip()
    if not q:
        return "错误：query 不能为空"
    if count < 1 or count > 50:
        return "错误：count 取值范围为 1-50"
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        return "错误：未设置 ZAI_API_KEY"
    try:
        from zai import ZhipuAiClient
    except ImportError:
        return "错误：未安装 zai-sdk 或当前 Python 环境不可用"
    try:
        client = ZhipuAiClient(api_key=api_key)
        resp = client.web_search.web_search(
            search_engine=search_engine,
            search_query=q,
            count=count,
            search_domain_filter=search_domain_filter,
            search_recency_filter=search_recency_filter,
            content_size=content_size,
        )
        plain = _to_plain(resp)
        try:
            return json.dumps(plain, ensure_ascii=False, indent=2, default=str)[:50000]
        except Exception:
            # 极端情况下退化为字符串，避免工具整体失败
            return str(resp)[:50000]
    except Exception as e:
        return f"错误：web_search 调用失败：{e}"
