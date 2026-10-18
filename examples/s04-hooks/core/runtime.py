"""第四课：有序前置检查与尽力后置观察，权限保持独立。"""
from copy import deepcopy
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / "s03-permission/core/runtime.py"
_spec = importlib.util.spec_from_file_location("s03_runtime", _path)
_s03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s03)
build_tools = _s03.build_tools
execute_guarded = _s03.execute_guarded
run_loop = _s03.run_loop
ask_claude = _s03.ask_claude
QUESTION = "先读 main.py，运行前问我；记录每次工具请求和处理结果，再报告结果。"


def run_hooks(hooks, event, payload):
    """before 按顺序遇阻即停；after 故障只记警告，并继续其他观察者。"""
    if event not in ("before", "after"):
        raise ValueError("未知 hook 事件")
    warnings = []
    for index, callback in enumerate(tuple(hooks.get(event, ()))):
        try:
            reason = callback(deepcopy(payload))
            if reason is not None:
                if event != "before" or not isinstance(reason, str) or not reason.strip():
                    raise ValueError("before 只能返回 None 或非空拒绝理由；after 必须返回 None")
                return {"blocked": reason, "warnings": warnings}
        except Exception as error:
            message = type(error).__name__ + ": " + str(error)
            if event == "before":
                return {"blocked": "前置检查异常：" + message, "warnings": warnings}
            warnings.append(message)
    return {"blocked": None, "warnings": warnings}


def execute_hooked(call, tools, ask_user, hooks, blocked=()):
    """包住上一课权限入口；后置观察故障不覆盖实际结果，也不重试工具。"""
    snapshot = deepcopy(call)
    before = run_hooks(hooks, "before", {"call": snapshot})
    if before["blocked"] is not None:
        result = {"type": "tool_result", "tool_use_id": snapshot["id"],
                  "content": "未执行：" + before["blocked"], "is_error": True}
    else:
        result = execute_guarded(snapshot, tools, ask_user, blocked)
    after = run_hooks(hooks, "after", {"call": snapshot, "result": result})
    return {"result": result, "warnings": after["warnings"]}


def audit_event(event, payload, entries):
    """只提取审计字段，既不修改请求，也不决定是否允许。"""
    call = payload["call"]
    entry = {"event": event, "id": call["id"], "tool": call["name"]}
    if event == "after":
        result = payload["result"]
        entry["is_error"] = result["is_error"]
        entry["content"] = result["content"]
    entries.append(entry)
