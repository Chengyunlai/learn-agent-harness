"""真实 SDK + MockTransport；不连接模型服务。"""
import json
import sys
import tempfile
from pathlib import Path
import httpx2 as httpx
from anthropic import Anthropic
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, ask_claude, build_tools, execute_tool, run_loop
from practice import scripted_model

requests = []
def handle(request):
    body = json.loads(request.content)
    requests.append(body)
    assert [tool["name"] for tool in body["tools"]] == ["read_file", "run_main"]
    assert body["tools"][0]["input_schema"]["required"] == ["path"]
    assert body["messages"][0]["content"] == QUESTION
    response = scripted_model(body["messages"])
    return httpx.Response(200, json={"id": "msg_test", "type": "message", "role": "assistant",
        "model": "test-model", "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 10}, **response})

with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory)
    (workspace / "main.py").write_text("print(6 * 7)\n")
    tools = build_tools(workspace)
    with Anthropic(api_key="teaching-placeholder", max_retries=0,
                   http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        result = run_loop(lambda messages: ask_claude(client, "test-model", messages, tools),
            lambda call: execute_tool(call, tools), emit=lambda _: None, question=QUESTION)
    assert result["status"] == "answered" and len(requests) == 3
    assert requests[1]["messages"][-1]["content"][0]["tool_use_id"] == "call_1"
    assert requests[2]["messages"][-1]["content"][0]["tool_use_id"] == "call_2"
    assert "42" in result["text"]
print("PASS SDK tool definitions, 3 simulated HTTP requests, associated results, real file/process")
