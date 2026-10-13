"""安装 requirements.txt 后验证真实 SDK + 模拟 HTTP；绝不访问在线模型。"""
import json
import sys
import tempfile
from pathlib import Path

import httpx2
from anthropic import Anthropic

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, SYSTEM, TOOLS, ask_claude, run_loop, run_main


requests = []


def respond(request):
    payload = json.loads(request.content)
    requests.append(payload)
    assert payload["model"] == "offline-contract-test"
    assert payload["system"] == SYSTEM and payload["tools"] == TOOLS
    assert payload["messages"][0]["content"] == QUESTION
    if len(requests) == 1:
        blocks = [
            {"type": "text", "text": "我会运行文件。", "citations": None},
            {"type": "tool_use", "id": "sdk_call_1", "name": "run_main", "input": {}},
        ]
        reason = "tool_use"
    else:
        result = payload["messages"][-1]["content"][0]
        assistant = payload["messages"][1]["content"]
        assert assistant[0] == {"type": "text", "text": "我会运行文件。"}
        assert assistant[1]["id"] == result["tool_use_id"] == "sdk_call_1"
        assert result["is_error"] and "ZeroDivisionError" in result["content"]
        blocks = [{"type": "text", "text": "运行失败：除零错误"}]
        reason = "end_turn"
    return httpx2.Response(200, json={
        "id": "msg_test", "type": "message", "role": "assistant",
        "model": "offline-contract-test", "content": blocks, "stop_reason": reason,
        "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1},
    })


with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory)
    (workspace / "main.py").write_text("print(10 / 0)\n")
    with Anthropic(
        api_key="offline-test-key", max_retries=0, timeout=20.0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
    ) as client:
        outcome = run_loop(
            lambda messages: ask_claude(client, "offline-contract-test", messages),
            lambda call: run_main(call, workspace), emit=lambda _: None,
        )
    assert outcome["status"] == "answered", outcome
    assert outcome["text"] == "运行失败：除零错误" and len(requests) == 2
print("PASS SDK 请求/响应转换、两次完整记录与结果关联；HTTP 全部模拟，Python 进程真实执行")
