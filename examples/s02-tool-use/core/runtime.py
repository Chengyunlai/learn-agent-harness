"""第二课：显式工具注册与分发，复用第一课的有限循环。"""
import importlib.util
from pathlib import Path

_first = Path(__file__).resolve().parents[2] / "s01-agent-loop/core/runtime.py"
_spec = importlib.util.spec_from_file_location("s01_runtime", _first)
_s01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s01)
run_loop = _s01.run_loop
QUESTION = "先读 main.py，再运行它，报告文件内容和运行结果。"
SYSTEM = "按用户要求选择工具。read_file 读取工作目录的短 UTF-8 文件；run_main 运行 main.py。不要修改文件。"


def read_file(workspace, path):
    """仅允许工作目录内的短 UTF-8 文件；路径约束不是进程沙箱。"""
    root = workspace.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError("路径越出工作目录。")
    with target.open("rb") as stream:
        data = stream.read(4097)
    if len(data) > 4096:
        raise ValueError("文件超过 4096 字节，请缩小读取范围。")
    return data.decode("utf-8")


def _run_main(workspace):
    result = _s01.run_main({"id": "internal", "name": "run_main", "input": {}}, workspace)
    if result["is_error"]:
        raise ValueError(result["content"])
    return result["content"]


def build_tools(workspace):
    """每项注册同时持有说明、参数形状和实现，供定义生成与分发共用。"""
    return {
        "read_file": {
            "description": "读取工作目录内最多 4096 字节的 UTF-8 文件，不修改文件。",
            "parameters": {"path": str},
            "run": lambda path: read_file(workspace, path),
        },
        "run_main": {
            "description": "运行工作目录的 main.py，返回退出码和输出，不接受参数。",
            "parameters": {},
            "run": lambda: _run_main(workspace),
        },
    }


def tool_definitions(tools):
    """本课只支持必填字符串参数；这是小型契约，不是通用 JSON Schema 校验器。"""
    return [{
        "name": name, "description": spec["description"],
        "input_schema": {
            "type": "object",
            "properties": {key: {"type": "string"} for key in spec["parameters"]},
            "required": list(spec["parameters"]), "additionalProperties": False,
        },
    } for name, spec in tools.items()]


def validate_call(call, tools):
    """本课小型参数契约；供分发与后续权限入口共用。"""
    name, arguments = call.get("name"), call.get("input")
    if not isinstance(name, str) or name not in tools:
        return "未知工具。"
    parameters = tools[name]["parameters"]
    if not isinstance(arguments, dict) or set(arguments) != set(parameters):
        return "参数字段不匹配。"
    if any(type(arguments[key]) is not kind for key, kind in parameters.items()):
        return "参数类型不匹配。"
    return None


def execute_tool(call, tools):
    """校验与执行；每个返回值保留原调用 ID。"""
    result = {"type": "tool_result", "tool_use_id": call["id"]}
    error = validate_call(call, tools)
    if error:
        return {**result, "content": error, "is_error": True}
    try:
        output = tools[call["name"]]["run"](**call["input"])
        return {**result, "content": output, "is_error": False}
    except (ValueError, OSError) as error:
        return {**result, "content": str(error), "is_error": True}


def ask_claude(client, model, messages, tools):
    response = client.messages.create(
        model=model, system=SYSTEM, messages=messages,
        tools=tool_definitions(tools), max_tokens=1024,
    )
    return response.model_dump(mode="json", exclude_none=True)
