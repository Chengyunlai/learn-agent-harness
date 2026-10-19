"""后台进程登记与轮次边界交接；复用原唯一循环。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

_path = Path(__file__).resolve().parents[2] / 's12-task-system/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s13_previous', _path)
_s12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s12)
_s11, _s10, _s07 = _s12._s11, _s12._s10, _s12._s07
run_loop = _s12.run_loop


def start_background(call, jobs, launch, allowed=False):
    """只启动固定main.py；收据只说明已启动，不说明运行成功。"""
    receipt = {"type": "tool_result", "tool_use_id": call["id"]}
    if call.get("name") != "run_background" or call.get("input") != {}:
        return {**receipt, "content": "未执行：工具或参数不支持。", "is_error": True}
    if call["id"] in jobs:
        return {**receipt, "content": jobs[call["id"]]["receipt"], "is_error": False}
    if allowed is not True or len(jobs) >= 4:
        return {**receipt, "content": "未执行：没有本次许可或会话登记已满。", "is_error": True}
    job_id = "bg-" + str(len(jobs) + 1)
    try:
        handle = launch()
    except OSError as error:
        return {**receipt, "content": "无法启动：" + str(error)[:160], "is_error": True}
    text = json.dumps({"job_id": job_id, "status": "started"})
    jobs[call["id"]] = {"job_id": job_id, "handle": handle, "receipt": text, "result": None}
    return {**receipt, "content": text, "is_error": False}


def collect_background(jobs):
    """非阻塞检查；完成记录留在登记表，直到会话结束。"""
    completed = []
    for call_id, job in jobs.items():
        if job["result"] is None:
            snapshot = job["handle"].snapshot()
            if snapshot is not None:
                job["result"] = {"job_id": job["job_id"], "call_id": call_id, **snapshot}
        if job["result"] is not None:
            completed.append(deepcopy(job["result"]))
    return completed


def prepare_background(history, jobs):
    """生成历史候选；通知是普通文本，不是原调用的第二个tool_result。"""
    candidate = deepcopy(history)
    for event in collect_background(jobs):
        text = "[background-result] " + json.dumps(event, ensure_ascii=False, sort_keys=True)
        present = any(message.get("role") == "user" and message.get("content") == text
                      for message in candidate)
        if not present:
            candidate.append({"role": "user", "content": text})
    return candidate


class ProcessHandle:
    """输出落临时文件避免管道填满；仅管理本课可信、无子进程的main.py。"""
    def __init__(self, workspace, timeout=3):
        self.output = tempfile.TemporaryFile()
        self.result = None
        self.deadline = time.monotonic() + timeout
        try:
            self.process = subprocess.Popen([sys.executable, 'main.py'], cwd=workspace,
                                            stdout=self.output, stderr=subprocess.STDOUT)
        except BaseException:
            self.output.close()
            raise

    def snapshot(self):
        if self.result is not None:
            return deepcopy(self.result)
        code = self.process.poll()
        timed_out = code is None and time.monotonic() >= self.deadline
        if code is None and not timed_out:
            return None
        if timed_out:
            self.process.kill()
            code = self.process.wait()
        self.output.seek(0)
        text = self.output.read(2000).decode('utf-8', errors='replace').strip()
        self.output.close()
        self.result = {'status': 'timeout' if timed_out else 'completed',
                       'exit_code': code, 'output': text, 'is_error': timed_out or code != 0}
        return deepcopy(self.result)

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        self.output.close()
