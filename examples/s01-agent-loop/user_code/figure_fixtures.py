"""Browser teaching fixtures. The formal functions execute; API/process boundaries are substitutes."""
import json
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, SYSTEM, TOOLS, ask_claude, run_main


def fixture_context(name, scenario="report"):
    if name not in ("ask_claude", "run_main", "run_loop"):
        raise ValueError("unknown teaching function")
    modes = {"ask_claude": ("request",), "run_main": ("error", "success", "timeout", "rejected"),
             "run_loop": ("report", "limit", "truncated")}
    if scenario not in modes[name]:
        raise ValueError("unknown teaching input")
    setup = f'''import json
from pathlib import Path
from types import SimpleNamespace
QUESTION = {QUESTION!r}
SYSTEM = {SYSTEM!r}
TOOLS = {TOOLS!r}
_scenario = {scenario!r}
_fixture_requests = []
_fixture_executions = []
sys = SimpleNamespace(executable="python")

class _Response:
    def __init__(self, data):
        self.data = data
    def model_dump(self, **options):
        return json.loads(json.dumps(self.data))

class _Messages:
    def create(self, **request):
        assert request["system"] == SYSTEM and request["tools"] == TOOLS
        _fixture_requests.append(json.loads(json.dumps(request)))
        if _scenario == "truncated":
            return _Response({{"stop_reason": "max_tokens", "content": []}})
        if len(request["messages"]) == 1:
            return _Response({{"stop_reason": "tool_use", "content": [{{
                "type": "tool_use", "id": "call_1", "name": "run_main", "input": {{}}
            }}]}})
        result = request["messages"][-1]["content"][0]
        text = "运行失败：除零错误" if "ZeroDivisionError" in result["content"] else result["content"]
        return _Response({{"stop_reason": "end_turn", "content": [{{"type": "text", "text": text}}]}})

class _TimeoutExpired(Exception):
    pass

class _Subprocess:
    TimeoutExpired = _TimeoutExpired
    def run(self, command, **options):
        assert command == ["python", "main.py"]
        _fixture_executions.append({{"command": command, "timeout": options["timeout"]}})
        if _scenario == "timeout":
            raise _TimeoutExpired(command, options["timeout"])
        success = _scenario == "success"
        return SimpleNamespace(returncode=0 if success else 1,
            stdout="ok\\n" if success else "",
            stderr="" if success else "ZeroDivisionError: division by zero\\n")

client = SimpleNamespace(messages=_Messages())
subprocess = _Subprocess()
'''
    if name == "ask_claude":
        entry = '''outcome = ask_claude(client, "教学模型", [{"role": "user", "content": QUESTION}])
print("stop_reason=" + outcome["stop_reason"] + " · id=" + outcome["content"][0]["id"])'''
        watch = ["model", "messages", "outcome"]
    elif name == "run_main":
        tool_name = "other_tool" if scenario == "rejected" else "run_main"
        entry = f'''outcome = run_main({{"id": "call_1", "name": {tool_name!r}, "input": {{}}}}, Path("/teaching"))
print(outcome["tool_use_id"], "· is_error=" + str(outcome["is_error"]))
print(outcome["content"])'''
        watch = ["call", "timeout", "result", "output", "outcome"]
    else:
        entry = f'''ask = lambda messages: ask_claude(client, "教学模型", messages)
execute = lambda call: run_main(call, Path("/teaching"))
outcome = run_loop(ask, execute, max_calls={1 if scenario == "limit" else 4}, emit=lambda text: None)
print(outcome["status"], "· 模型调用", outcome["calls"], "· 记录", len(outcome["messages"]))
print(outcome["text"])'''
        watch = ["messages", "number", "reason", "results", "result", "outcome"]
    if name == "run_loop":
        setup += "\n" + inspect.getsource(ask_claude) + "\n" + inspect.getsource(run_main)
    return {"setup": setup, "entry": entry, "watch": watch,
            "scopes": [name, "finish"] if name == "run_loop" else [name]}


if __name__ == "__main__":
    print(json.dumps({name: {case: fixture_context(name, case) for case in cases}
                      for name, cases in {"ask_claude": ["request"],
                        "run_main": ["error", "success", "timeout", "rejected"],
                        "run_loop": ["report", "limit", "truncated"]}.items()}, ensure_ascii=False))
