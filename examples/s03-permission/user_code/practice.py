"""Permission 公开入口：默认询问终端用户，非交互环境按拒绝处理。"""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, ask_claude, build_tools, execute_guarded, run_loop


def scripted_model(messages):
    count = sum(message["role"] == "assistant" for message in messages)
    if count < 2:
        return {"stop_reason": "tool_use", "content": [{
            "type": "tool_use", "id": "read_1" if count == 0 else "run_1",
            "name": "read_file" if count == 0 else "run_main",
            "input": {"path": "main.py"} if count == 0 else {},
        }]}
    result = messages[-1]["content"][0]
    text = "已读取文件；" + (result["content"] if not result["is_error"] else "本次未运行 main.py。" + result["content"])
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


def terminal_approval(call, reason):
    print(f"等待允许：{call['id']} · {call['name']} · {call['input']}\n{reason}")
    if not sys.stdin.isatty():
        print("非交互输入，按未获允许处理")
        return False
    try:
        return input("允许这一次？[y/N] ").strip().lower() == "y"
    except EOFError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", choices=["ask", "allow", "deny"], default="ask",
                        help="allow/deny 为本次教学运行的一次固定宿主回答")
    parser.add_argument("--block-run", action="store_true")
    parser.add_argument("--max-calls", type=int, default=4)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent / "workspace")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls 必须至少为 1")
    tools = build_tools(args.workspace.resolve())
    answers = iter([args.decision == "allow"])
    def approve(call, reason):
        if args.decision == "ask":
            return terminal_approval(call, reason)
        answer = next(answers, False)
        print(f"教学宿主回答：{call['id']} · allow={answer}")
        return answer
    if args.live:
        if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("ANTHROPIC_MODEL"):
            parser.error("--live 需要 ANTHROPIC_API_KEY 和 ANTHROPIC_MODEL")
        from anthropic import Anthropic
        client = Anthropic(timeout=20.0, max_retries=0)
        ask = lambda messages: ask_claude(client, os.environ["ANTHROPIC_MODEL"], messages, tools)
        print("在线模型；仅允许后才启动文件")
    else:
        ask = scripted_model
        print("离线模型替身；读取真实文件，执行取决于权限结果")
    execute = lambda call: execute_guarded(call, tools, approve, ("run_main",) if args.block_run else ())
    outcome = run_loop(ask, execute, args.max_calls, question=QUESTION)
    print("停止状态：" + outcome["status"])
    print(outcome["text"])
    return 0 if outcome["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
