"""公开浏览器绑定：正式函数原样执行，文件/进程边界使用可查看的替身。"""
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import build_tools, execute_tool, read_file, validate_call

CASES = {"build_tools": ["registry"], "execute_tool": ["read", "run", "unknown", "arguments"],
         "read_file": ["read", "outside", "large"]}


def fixture_context(name, scenario):
    if scenario not in CASES[name]:
        raise ValueError("unknown fixture")
    setup = '''import io
from pathlib import PurePosixPath
_files = {"/teaching/main.py": b"print(6 * 7)\\n", "/teaching/large": b"x" * 4097}
_reads = []
_runs = []
class _Path:
    def __init__(self, path):
        self.path = PurePosixPath(path)
    def resolve(self):
        parts = []
        for part in self.path.parts:
            if part == "..":
                if parts: parts.pop()
            elif part not in ("/", "."): parts.append(part)
        return _Path("/" + "/".join(parts))
    def __truediv__(self, path):
        return _Path(self.path / path)
    def is_relative_to(self, root):
        return self.path.is_relative_to(root.path)
    def open(self, mode):
        assert mode == "rb"
        _reads.append(str(self.path))
        return io.BytesIO(_files[str(self.path)])
workspace = _Path("/teaching")
def _run_main(workspace):
    _runs.append("main.py")
    return "exit_code=0\\n42"
'''
    for helper in [read_file, build_tools, validate_call]:
        if name != helper.__name__:
            setup += "\n" + inspect.getsource(helper)
    if name == "build_tools":
        entry = 'outcome = build_tools(workspace)\nprint("已注册：", ", ".join(outcome))'
        watch = ["outcome"]
    elif name == "execute_tool":
        tool_name = "delete_file" if scenario == "unknown" else "run_main" if scenario == "run" else "read_file"
        arguments = {} if scenario == "run" else {"path": 42 if scenario == "arguments" else "main.py"}
        entry = f'''outcome = execute_tool({{"id": "call_1", "name": {tool_name!r}, "input": {arguments!r}}}, build_tools(workspace))
print("call_1", "is_error=" + str(outcome["is_error"]))
print(outcome["content"])'''
        watch = ["call", "name", "arguments", "output", "outcome", "parameters"]
    else:
        path = {"read": "main.py", "outside": "../secret.txt", "large": "large"}[scenario]
        entry = f'''try:
    outcome = read_file(workspace, {path!r})
except (ValueError, OSError) as error:
    outcome = str(error)
print(outcome)'''
        watch = ["path", "data", "outcome"]
    return {"setup": setup, "entry": entry, "watch": watch, "scopes": [name]}


if __name__ == "__main__":
    print(json.dumps({name: {case: fixture_context(name, case) for case in cases}
                      for name, cases in CASES.items()}, ensure_ascii=False))
