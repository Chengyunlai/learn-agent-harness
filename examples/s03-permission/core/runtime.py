"""第三课：在实际执行前分离策略、宿主确认和执行入口。"""
from copy import deepcopy
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / "s02-tool-use/core/runtime.py"
_spec = importlib.util.spec_from_file_location("s02_runtime", _path)
_s02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s02)
build_tools = _s02.build_tools
execute_tool = _s02.execute_tool
validate_call = _s02.validate_call
run_loop = _s02.run_loop
QUESTION = "先读 main.py；运行之前问我，得到允许后再运行并报告结果。"
SYSTEM = "按用户要求工作。权限由宿主决定；收到未获批准的结果时如实报告，不反复请求。"


def permission_for(call, tools, blocked=()):
    """只判断，不提问、不执行。没有策略的工具默认拒绝。"""
    error = validate_call(call, tools)
    if error:
        return {"decision": "deny", "reason": error}
    name = call["name"]
    if name in blocked:
        return {"decision": "deny", "reason": "宿主策略禁止这个工具。"}
    if name == "read_file":
        return {"decision": "allow", "reason": "允许读取；目录约束仍由读取函数检查。"}
    if name == "run_main":
        return {"decision": "ask", "reason": "运行 main.py 前需要用户允许。"}
    return {"decision": "deny", "reason": "这个工具尚未配置权限策略。"}


def authorize_call(call, tools, ask_user, blocked=()):
    """只有 ask 才调用宿主；必须收到布尔 True 才允许。"""
    verdict = permission_for(call, tools, blocked)
    if verdict["decision"] != "ask":
        return verdict
    # 宿主看到调用副本；不能通过修改显示对象改变后续执行参数。
    answer = ask_user(deepcopy(call), verdict["reason"])
    if answer is True:
        return {"decision": "allow", "reason": "用户允许本次调用。"}
    return {"decision": "deny", "reason": "本次调用未获用户允许。"}


def execute_guarded(call, tools, ask_user, blocked=()):
    """验证、显示与执行使用同一份调用快照；拒绝结果不冒充执行结果。"""
    snapshot = deepcopy(call)
    verdict = authorize_call(snapshot, tools, ask_user, blocked)
    if verdict["decision"] != "allow":
        return {
            "type": "tool_result", "tool_use_id": snapshot["id"],
            "content": "未执行：" + verdict["reason"], "is_error": True,
        }
    return execute_tool(snapshot, tools)


def ask_claude(client, model, messages, tools):
    response = client.messages.create(
        model=model, system=SYSTEM, messages=messages,
        tools=_s02.tool_definitions(tools), max_tokens=1024,
    )
    return response.model_dump(mode="json", exclude_none=True)
