"""固定模型；真实双线程、持久看板/邮箱、获准后的Python进程。"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import *
from runtime import _s07, _s10, _s11


def fixed_model(messages, actor, task_id):
    if actor == "lead":
        return _s10.answer(
            "已接入队友反馈；看板终态：" + messages[0]["content"].split("\n", 1)[1]
        )
    anchor = max(
        i
        for i, m in enumerate(messages)
        if isinstance(m["content"], str) and m["content"].startswith("[auto-turn]")
    )
    count = sum(m["role"] == "assistant" for m in messages[anchor + 1 :])
    if count == 0:
        name, args = (
            ("run_main", {})
            if task_id == "verify"
            else (
                "read_file",
                {"path": "main.py" if task_id == "source" else "expected.txt"},
            )
        )
        response = _s10.use(name, args, 1)
        response["content"][0]["id"] = f"{actor}-{task_id}-1"
        return response
    result = next(
        b
        for m in messages[anchor + 1 :]
        if isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result" and b.get("tool_use_id") == f"{actor}-{task_id}-1"
    )
    return _s10.answer("本轮实际工具反馈：" + result["content"])


def run_job(
    previous,
    actor,
    task,
    board_dir,
    mail,
    team,
    workspace,
    allowed,
    lock,
    traces,
    send_override=None,
):
    task_id = task["id"]
    tools = _s07._s02.build_tools(workspace)
    tools = {
        key: tools[key]
        for key in (("run_main",) if task_id == "verify" else ("read_file",))
    }
    cache, recovery = {}, {"remaining": 20, "waited": 0.0, "events": []}

    def prepare(current):
        return prepare_inbox(previous + current, mail, team, actor, lock)[len(previous) :]

    def ask(current):
        request = {
            "model": "teaching-model",
            "system": _s10.get_system_prompt(
                _s10.collect_context(workspace, tools, {}, []), cache
            )["system"]
            + "\n宿主成员："
            + actor,
            "tools": _s07._s02.tool_definitions(tools),
            "messages": previous + current,
            "max_tokens": 1024,
        }
        with lock:
            traces.append(
                {"actor": actor, "task_id": task_id, "request": deepcopy(request)}
            )
        return _s11.request_with_recovery(
            send_override or (lambda req: fixed_model(req["messages"], actor, task_id)),
            request,
            recovery,
            pause=lambda _: None,
            random_unit=lambda: 0,
        )

    def owner_guard(payload):
        with lock:
            current = load_board(board_dir)["tasks"][task_id]
            if current["status"] != "in_progress" or current["owner"] != actor:
                return "当前成员没有持有这项任务。"
        call = payload["call"]
        if task_id != "verify" and call.get("input") != {
            "path": "main.py" if task_id == "source" else "expected.txt"
        }:
            return "只能读取本项登记文件。"
        return None

    def execute(call):
        return _s07._s04.execute_hooked(
            call, tools, lambda *_: allowed, {"before": [owner_guard]}
        )["result"]

    outcome = run_loop(
        ask,
        execute,
        max_calls=4,
        emit=lambda _: None,
        prepare=prepare,
        question=f"[auto-turn] {actor}:{task_id}\n完成本项固定工具调用，如实报告反馈。",
    )
    current = outcome["messages"]
    results = [
        b
        for m in current
        if isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    ]
    outcome["evidence"] = results[-1] if results else None
    outcome["messages"] = previous + current
    return outcome


def finish_job(directory, task, actor, outcome, lock):
    evidence = outcome.get("evidence")
    if outcome["status"] != "answered" or evidence is None or evidence["is_error"]:
        return {"status": "needs_attention", "reason": "没有成功工具证据，保留认领。"}
    result = evidence["content"].strip()
    if not result:
        return {"status": "needs_attention", "reason": "证据为空，保留认领。"}
    with lock:
        board = load_board(directory)
        if task["id"] == "verify":
            expected = board["tasks"]["expected"]["result"].strip()
            if result != "exit_code=0\n" + expected:
                return {
                    "status": "needs_attention",
                    "reason": "本次输出与预期不符，保留认领。",
                }
        saved = complete_task(directory, task["id"], actor, result)
    return {"status": "completed", "task_id": task["id"], "unlocked": saved["unlocked"]}


def demo(root, workspace, allowed=False, send_override=None, on_claim=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("本课使用空状态目录，不恢复旧成员或重试未决工作。")
    board_dir, mail = root / "board", root / "mail"
    for key, subject, deps in [
        ("source", "读取main.py源码", []),
        ("expected", "读取expected.txt预期", []),
        ("verify", "运行并核对本次输出", ["source", "expected"]),
    ]:
        create_task(board_dir, key, subject, "宿主登记的固定步骤，不开放任意命令。", deps)
    team, protocols, lock, traces, reports, stops = (
        create_team(),
        {},
        threading.RLock(),
        [],
        [],
        {},
    )
    for name in ("reader", "reviewer"):
        team[name]["role"] = "自行发现并执行看板上的固定任务"
    stop = threading.Event()

    def worker(actor):
        try:
            for _ in range(2):
                picked = idle_poll(board_dir, team, protocols, mail, actor, lock, stop.wait)
                if picked["status"] != "claimed":
                    with lock:
                        stops[actor] = picked["status"]
                    break
                task = picked["task"]
                box = {}
                if on_claim:
                    on_claim(actor, deepcopy(task))
                send = (
                    (lambda req: send_override(actor, task["id"], req))
                    if send_override
                    else None
                )

                def turn(previous):
                    result = run_job(
                        previous,
                        actor,
                        task,
                        board_dir,
                        mail,
                        team,
                        workspace,
                        allowed,
                        lock,
                        traces,
                        send,
                    )
                    box["outcome"] = result
                    return result

                result = run_teammate(team, actor, turn, lock)
                saved = finish_job(board_dir, task, actor, box.get("outcome", result), lock)
                with lock:
                    reports.append({"actor": actor, "task_id": task["id"], **saved})
                    send_message(
                        mail,
                        team,
                        actor,
                        "lead",
                        json.dumps({"task_id": task["id"], **saved}, ensure_ascii=False),
                        lock,
                    )
                if saved["status"] != "completed":
                    with lock:
                        stops[actor] = "needs_attention"
                    break
            else:
                with lock:
                    stops[actor] = "delivery_limit"
        except Exception as error:
            with lock:
                stops[actor] = type(error).__name__

    threads = [
        threading.Thread(target=worker, args=(actor,), name="s17-" + actor)
        for actor in ("reader", "reviewer")
    ]
    try:
        for thread in threads:
            thread.start()
    finally:
        for thread in threads:
            if thread.ident is not None:
                thread.join()
    # Every worker has stopped before the host performs final cooperative closure.
    for actor in ("reader", "reviewer"):
        open_request(
            protocols,
            team,
            mail,
            "lead",
            actor,
            "shutdown",
            "会话结束，请在空闲边界确认关闭。",
            lock,
        )
        if team[actor]["status"] == "idle":
            idle_poll(board_dir, team, protocols, mail, actor, lock, stop.wait, checks=1)
    consume_responses(protocols, team, mail, "lead", lock)
    board = load_board(board_dir)
    messages = prepare_inbox(
        [
            {
                "role": "user",
                "content": "[auto-turn] lead:summary\n"
                + json.dumps(board["tasks"], ensure_ascii=False),
            }
        ],
        mail,
        team,
        "lead",
        lock,
    )
    request = {
        "model": "teaching-model",
        "system": "仅汇总已保存任务与收到的反馈；in_progress不能说已完成。",
        "tools": [],
        "messages": messages,
        "max_tokens": 1024,
    }
    with lock:
        traces.append({"actor": "lead", "task_id": "summary", "request": deepcopy(request)})
    recovery = {"remaining": 20, "waited": 0.0, "events": []}
    lead = _s11.request_with_recovery(
        (
            (lambda req: send_override("lead", "summary", req))
            if send_override
            else (lambda req: fixed_model(req["messages"], "lead", "summary"))
        ),
        request,
        recovery,
        pause=lambda _: None,
        random_unit=lambda: 0,
    )
    return {
        "board": board,
        "team": team,
        "protocols": protocols,
        "traces": traces,
        "reports": reports,
        "stops": stops,
        "lead": lead,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", choices=["allow", "deny"], default="deny")
    parser.add_argument(
        "--workspace", type=Path, default=Path(__file__).parent / "workspace"
    )
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()

    def show(folder):
        result = demo(folder, args.workspace.resolve(), args.decision == "allow")
        print("固定模型；真实双线程、文件看板/邮箱与获准后的Python进程；没有在线模型。")
        print("自主处理记录：", result["reports"])
        print(
            "看板：",
            [
                (key, item["status"], item["owner"])
                for key, item in result["board"]["tasks"].items()
            ],
        )
        print("停止原因：", result["stops"])
        print("成员：", {key: item["status"] for key, item in result["team"].items()})
        print("逻辑请求：", len(result["traces"]))
        print(result["lead"]["content"][0]["text"])

    if args.state_dir:
        show(args.state_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="s17-auto-") as folder:
            show(Path(folder))


if __name__ == "__main__":
    main()
