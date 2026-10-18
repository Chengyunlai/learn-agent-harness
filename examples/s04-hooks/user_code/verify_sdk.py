"""Hook反馈经过真实SDK的模拟HTTP往返；不调用在线模型。"""
import json
import sys
import tempfile
from pathlib import Path
import httpx2 as httpx
from anthropic import Anthropic
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, ask_claude, build_tools, execute_hooked, run_loop
from practice import scripted_model, build_hooks

for maintenance in (False, True):
    requests = []
    def handle(request):
        body = json.loads(request.content); requests.append(body)
        assert body["messages"][0]["content"] == QUESTION
        response = scripted_model(body["messages"])
        return httpx.Response(200, json={"id": "msg_demo", "type": "message", "role": "assistant",
            "model": "teaching-model", "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 10}, **response})
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "main.py").write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n")
        tools = build_tools(root)
        with Anthropic(api_key="teaching-placeholder", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            outcome = run_loop(lambda m: ask_claude(client, "teaching-model", m, tools),
                lambda c: execute_hooked(c, tools, lambda *_: True, build_hooks([], maintenance, audit_failure=True))["result"],
                emit=lambda _: None, question=QUESTION)
        assert outcome["status"] == "answered" and len(requests) == 3
        result = requests[2]["messages"][-1]["content"][0]
        assert result["tool_use_id"] == "run_1" and result["is_error"] == maintenance
        assert (root / "ran").exists() == (not maintenance)
    print("PASS SDK HTTP simulated; maintenance=", maintenance, "correct result and real program marker")
