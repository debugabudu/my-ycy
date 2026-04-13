import uuid

from ycy.constants import LEAD_ACTOR_ID
from ycy.team.bus import MessageBus

shutdown_requests: dict = {}
plan_requests: dict = {}


def handle_shutdown_request(bus: MessageBus, teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    bus.send(
        LEAD_ACTOR_ID,
        teammate,
        "请结束运行。",
        "shutdown_request",
        {"request_id": req_id},
    )
    return f"已向「{teammate}」发送关闭请求（编号 {req_id}）。"


def handle_plan_review(
    bus: MessageBus, request_id: str, approve: bool, feedback: str = ""
) -> str:
    req = plan_requests.get(request_id)
    if not req:
        return f"错误：未知的计划请求 id「{request_id}」"
    req["status"] = "approved" if approve else "rejected"
    bus.send(
        LEAD_ACTOR_ID,
        req["from"],
        feedback,
        "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    st = "已通过" if req["status"] == "approved" else "已驳回"
    return f"计划{st}（来自「{req['from']}」）"
