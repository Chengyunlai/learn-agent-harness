"""第十七课：同进程队友发现并原子认领工作，空闲边界优先处理关闭。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_root = Path(__file__).resolve().parents[2]
_s16 = module_at("s17_previous", _root / "s16-team-protocols/core/runtime.py")
_tasks = module_at("s17_tasks", _root / "s12-task-system/core/runtime.py")
member_name, create_team, run_teammate = (
    _s16.member_name,
    _s16.create_team,
    _s16.run_teammate,
)
load_inbox, send_message, prepare_inbox = (
    _s16.load_inbox,
    _s16.send_message,
    _s16.prepare_inbox,
)
read_protocol = _s16.read_protocol
open_request, reply_request, consume_responses = (
    _s16.open_request,
    _s16.reply_request,
    _s16.consume_responses,
)
run_loop, _s07, _s10, _s11 = _s16.run_loop, _s16._s07, _s16._s10, _s16._s11
checked_board, load_board, claim_task = (
    _tasks.checked_board,
    _tasks.load_board,
    _tasks.claim_task,
)
create_task, complete_task = _tasks.create_task, _tasks.complete_task


def scan_ready(board):
    """只返回快照中的可认领ID，不写负责人，也不运行任务。"""
    tasks = checked_board(board)["tasks"]
    ready = []
    for task_id in sorted(tasks):
        task = tasks[task_id]
        if task["status"] != "pending" or task["owner"] is not None:
            continue
        if all(tasks[dep]["status"] == "completed" for dep in task["blocked_by"]):
            ready.append(task_id)
    return ready


def claim_next(directory, team, name, lock):
    """同一把锁内重新读盘、扫描、认领；成功保存才交出任务。"""
    member_name(name, team)
    with lock:
        member = team[name]
        if (
            name == "lead"
            or member["active"]
            or member["status"] != "idle"
            or member["turns"] >= 2
        ):
            return {"status": "unavailable"}
        board = load_board(directory)
        if any(
            t["owner"] == name and t["status"] == "in_progress"
            for t in board["tasks"].values()
        ):
            return {"status": "busy"}
        ready = scan_ready(board)
        if not ready:
            return {"status": "idle"}
        task = claim_task(directory, ready[0], name)
    return {"status": "claimed", "task": task}


def shutdown_at_boundary(state, team, mail, name, lock):
    """仅处理发给自己的真实关闭请求；普通消息不唤起空转模型。"""
    messages = load_inbox(mail, name, team)
    for message in messages:
        try:
            data = read_protocol(message)
        except (ValueError, TypeError):
            continue
        if data is None or data.get("type") != "shutdown_request":
            continue
        request_id = data["request_id"]
        record = state.get(request_id)
        if (
            record is None
            or record["kind"] != "shutdown"
            or record["target"] != name
            or record["sender"] != message["sender"]
            or record["payload"] != data.get("payload")
            or record["status"] != "pending"
        ):
            continue
        receipt = reply_request(
            state, team, mail, request_id, name, True, "空闲边界确认关闭。", lock
        )
        return {
            "status": "shutdown",
            "request_id": request_id,
            "reply_status": receipt["status"],
        }
    return None


def idle_poll(directory, team, state, mail, name, lock, wait, checks=3):
    """只做有界宿主检查；关闭优先，没有工作就等待，不调用模型。"""
    member_name(name, team)
    if type(checks) is not int or not 1 <= checks <= 12:
        raise ValueError("检查次数需要1到12。")
    for index in range(checks):
        with lock:
            member = team[name]
            if name == "lead" or member["active"] or member["status"] != "idle":
                return {"status": "unavailable"}
            control = shutdown_at_boundary(state, team, mail, name, lock)
            if control is not None:
                return control
            outcome = claim_next(directory, team, name, lock)
            if outcome["status"] != "idle":
                return outcome
        if index + 1 < checks:
            if wait(0.05):
                return {"status": "interrupted"}
    return {"status": "idle_timeout", "checks": checks}
