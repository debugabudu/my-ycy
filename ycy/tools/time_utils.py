import json
from datetime import datetime


def run_current_time() -> str:
    now = datetime.now().astimezone()
    payload = {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timezone": str(now.tzinfo),
        "unix": int(now.timestamp()),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
