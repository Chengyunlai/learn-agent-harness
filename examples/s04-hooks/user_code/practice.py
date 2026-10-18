"""Hooks 公开入口；离线模型、真实文件/进程，默认运行前询问。"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, ask_claude, audit_event, build_tools, execute_hooked, run_loop

_spec = importlib.util.spec_from_file_location("s03_practice", Path(__file__).resolve().parents[2] / "s03-permission/user_code/practice.py")
_previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_previous)
terminal_approval = _previous.terminal_approval


def scripted_model(messages):
    count = sum(m["role"] == "assistant" for m in messages)
    if count < 2:
        return {"stop_reason": "tool_use", "content": [{"type": "tool_use",
            "id": "read_1" if count == 0 else "run_1",
            "name": "read_file" if count == 0 else "run_main",
            "input": {"path": "main.py"} if count == 0 else {}}]}
    result = messages[-1]["content"][0]
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": result["content"]}]}


def build_hooks(entries, maintenance=False, audit_failure=False):
    def check(payload):
        if maintenance and payload["call"]["name"] == "run_main":
            return "维护期间暂停运行。"
    def audit_before(payload):
        audit_event("before", payload, entries)
    def audit_after(payload):
        if audit_failure:
            raise OSError("教学审计写入失败")
        audit_event("after", payload, entries)
    return {"before": [audit_before, check], "after": [audit_after]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", choices=["ask", "allow", "deny"], default="ask")
    parser.add_argument("--maintenance", action="store_true")
    parser.add_argument("--audit-failure", action="store_true")
    parser.add_argument("--block-run", action="store_true")
    parser.add_argument("--max-calls", type=int, default=4)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent / "workspace")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.max_calls < 1: parser.error("--max-calls 必须至少为 1")
    tools = build_tools(args.workspace.resolve())
    entries, warnings = [], []
    hooks = build_hooks(entries, args.maintenance, args.audit_failure)
    answers = iter([args.decision == "allow"])
    def approve(call, reason):
        if args.decision == "ask": return terminal_approval(call, reason)
        return next(answers, False)
    def execute(call):
        report = execute_hooked(call, tools, approve, hooks, ("run_main",) if args.block_run else ())
        warnings.extend(report["warnings"])
        return report["result"]
    if args.live:
        if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("ANTHROPIC_MODEL"):
            parser.error("--live 需要 ANTHROPIC_API_KEY 和 ANTHROPIC_MODEL")
        from anthropic import Anthropic
        client = Anthropic(timeout=20.0, max_retries=0)
        ask = lambda messages: ask_claude(client, os.environ["ANTHROPIC_MODEL"], messages, tools)
        print("在线模型；文件/进程真实执行，权限与 hooks 由宿主处理")
    else:
        ask = scripted_model
        print("离线模型替身；真实读文件，获准后真实运行；审计保存在内存")
    outcome = run_loop(ask, execute, args.max_calls, question=QUESTION)
    print("停止状态：" + outcome["status"])
    print(outcome["text"])
    for entry in entries: print("审计：", entry)
    for warning in warnings: print("宿主警告：", warning)
    return 0 if outcome["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
