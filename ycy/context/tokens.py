import json


def estimate_tokens(messages: list) -> int:
    return len(json.dumps(messages, default=str)) // 4
