"""独立验证教学短代码的真实行前快照与三条停止路径；仅标准库。"""
import contextlib
import copy
import io
import sys
from pathlib import Path

source = Path(__file__).with_name("reading_demo.py").read_text()
filename = "<reading-demo>"
save = next(i for i, line in enumerate(source.splitlines(), 1)
            if 'messages.append({"role": "user", "content": [result]})' in line)


def run(code):
    frames, executions = [], []
    namespace = {"__name__": "__main__"}
    output = io.StringIO()

    def trace(frame, event, _):
        if frame.f_code.co_filename == filename:
            if event == "call" and frame.f_code.co_name == "execute":
                executions.append(len(frame.f_globals["messages"]))
            if event == "line" and frame.f_code.co_name == "<module>":
                values = {key: copy.deepcopy(value) for key, value in frame.f_locals.items()
                          if key in ("number", "messages", "response", "result")}
                frames.append((frame.f_lineno, values, output.getvalue()))
            return trace

    previous = sys.gettrace()
    try:
        with contextlib.redirect_stdout(output):
            sys.settrace(trace)
            exec(compile(code, filename, "exec"), namespace)
    finally:
        sys.settrace(previous)
    return namespace, frames, executions, output.getvalue()


normal, frames, executions, output = run(source)
index = next(i for i, (line, _, _) in enumerate(frames) if line == save)
before, after = frames[index][1], frames[index + 1][1]
assert len(before["messages"]) == 2 and len(after["messages"]) == 3
assert before["result"]["is_error"] and "ZeroDivisionError" in before["result"]["content"]
assert before["result"]["tool_use_id"] == before["response"]["content"][0]["id"]
assert normal["number"] == 2 and len(normal["messages"]) == 4 and executions == [2]
assert output == "保存 call_1 ；记录 3\nanswered： 运行失败：除零错误\n"

limited, _, executions, output = run(source.replace("max_calls = 4", "max_calls = 1", 1))
assert limited["number"] == 1 and len(limited["messages"]) == 3 and executions == [2]
assert "call_limit： 1 次调用；结果已保存" in output and "answered" not in output

truncated, _, executions, output = run(source.replace("truncated = False", "truncated = True", 1))
assert truncated["number"] == 1 and len(truncated["messages"]) == 2 and not executions
assert "result" not in truncated and output == "model_stopped： max_tokens\n"
print("PASS reading demo: record before/after, associated error, two calls, budget stop, truncation never executes")
