"""第二课公开入口；模型默认替身，文件读取与 Python 进程真实执行。"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, ask_claude, build_tools, execute_tool, run_loop


def scripted_model(messages):
    count = sum(message["role"] == "assistant" for message in messages)
    if count < 2:
        return {"stop_reason": "tool_use", "content": [{
            "type": "tool_use", "id": f"call_{count + 1}",
            "name": "read_file" if count == 0 else "run_main",
            "input": {"path": "main.py"} if count == 0 else {},
        }]}
    read = messages[2]["content"][0]
    run = messages[4]["content"][0]
    answer = f"文件内容：{read['content'].strip()}\n运行结果：{run['content']}"
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": answer}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent / "workspace")
    parser.add_argument("--max-calls", type=int, default=4)
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls 必须至少为 1")
    tools = build_tools(args.workspace.resolve())
    if args.live:
        if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("ANTHROPIC_MODEL"):
            parser.error("--live 需要 ANTHROPIC_API_KEY 和 ANTHROPIC_MODEL")
        from anthropic import Anthropic
        client = Anthropic(timeout=20.0, max_retries=0)
        ask = lambda messages: ask_claude(client, os.environ["ANTHROPIC_MODEL"], messages, tools)
        print("在线模型；文件与进程真实执行")
    else:
        ask = scripted_model
        print("离线模型替身；文件与进程真实执行")
    outcome = run_loop(ask, lambda call: execute_tool(call, tools),
                       args.max_calls, question=QUESTION)
    print("停止状态：" + outcome["status"])
    print(outcome["text"])
    return 0 if outcome["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
