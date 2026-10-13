"""公开入口；默认离线，只有 --live 才调用真实 Claude API。"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import ask_claude, run_loop, run_main


def scripted_model(messages):
    """可复现的测试替身：不调用模型，真实执行 main.py。"""
    if len(messages) == 1:
        return {"stop_reason": "tool_use", "content": [{
            "type": "tool_use", "id": "demo_call_1", "name": "run_main", "input": {},
        }]}
    result = messages[-1]["content"][0]
    answer = "运行失败：除零错误" if "ZeroDivisionError" in result["content"] else result["content"]
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": answer}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="使用真实 Claude API")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent / "workspace")
    parser.add_argument("--max-calls", type=int, default=4)
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls 必须至少为 1")
    if args.live:
        if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("ANTHROPIC_MODEL"):
            parser.error("真实调用需要 ANTHROPIC_API_KEY 和 ANTHROPIC_MODEL 环境变量")
        from anthropic import Anthropic
        # 关闭 SDK 自动重试，模型调用计数与实际请求次数对应；网络超时单独设置。
        client = Anthropic(timeout=20.0, max_retries=0)
        ask = lambda messages: ask_claude(client, os.environ["ANTHROPIC_MODEL"], messages)
        print("真实模型模式；执行指定目录中的 main.py")
    else:
        ask = scripted_model
        print("离线模式：模型响应为测试替身，main.py 真实执行")
    outcome = run_loop(ask, lambda call: run_main(call, args.workspace.resolve()), args.max_calls)
    print("停止状态：" + outcome["status"])
    print(outcome["text"])
    return 0 if outcome["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
