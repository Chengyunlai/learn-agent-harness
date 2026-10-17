"""正式权限函数正文的浏览器教学输入；宿主/文件/进程边界为可查看替身。"""
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import permission_for, authorize_call, execute_guarded, validate_call, execute_tool

FUNCTIONS = (permission_for, authorize_call, execute_guarded)
CASES = {"permission_for": ["read", "ask", "blocked", "invalid"],
         "authorize_call": ["approved", "refused", "blocked", "not_boolean"],
         "execute_guarded": ["approved", "refused", "blocked", "read", "mutated"]}


def fixture_context(name, scenario):
    if scenario not in CASES[name]: raise ValueError("unknown teaching input")
    setup = f'''from copy import deepcopy
_scenario = {scenario!r}
_executions = []
_approvals = []
def _read_file(path):
    _executions.append("read_file")
    return "print(6 * 7)\\n"
def _run_main():
    _executions.append("run_main")
    return "exit_code=0\\n42"
tools = {{"read_file": {{"parameters": {{"path": str}}, "run": _read_file}},
         "run_main": {{"parameters": {{}}, "run": _run_main}}}}
blocked = ("run_main",) if _scenario == "blocked" else ()
call = {{"type": "tool_use", "id": "run_1", "name": "run_main", "input": {{}}}}
if _scenario == "read":
    call.update(id="read_1", name="read_file", input={{"path": "main.py"}})
if _scenario == "invalid":
    call["input"] = {{"approved": True}}
def ask_user(shown, reason):
    _approvals.append(deepcopy(shown))
    if _scenario == "mutated":
        shown.update(name="unknown", input={{"path": "changed"}})
    if _scenario == "not_boolean": return "yes"
    return _scenario in ("approved", "mutated")
'''
    helpers = (validate_call, execute_tool, permission_for, authorize_call)
    for helper in helpers:
        if helper.__name__ != name:
            setup += "\n" + inspect.getsource(helper)
    if name == "permission_for":
        entry = 'outcome = permission_for(call, tools, blocked)\nprint(outcome["decision"])'
    else:
        entry = f'''outcome = {name}(call, tools, ask_user, blocked)
print("实际执行：" + ("、".join(_executions) or "无"))'''
    return {"setup": setup, "entry": entry,
            "watch": ["call", "snapshot", "verdict", "answer", "outcome"], "scopes": [name]}


if __name__ == "__main__":
    print(json.dumps({name: {case: fixture_context(name, case) for case in cases}
                      for name, cases in CASES.items()}, ensure_ascii=False))
