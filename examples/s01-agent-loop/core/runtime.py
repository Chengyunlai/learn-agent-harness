"""第一课实践：一个客户端工具、内存记录、有限次模型调用。"""
import subprocess
import sys
from pathlib import Path


QUESTION = "运行 main.py，只报告结果。"
SYSTEM = "按用户要求工作。需要运行 main.py 时调用 run_main；收到结果后如实报告，不修改文件。"
TOOLS = [{
    "name": "run_main",
    "description": "运行工作目录中的 main.py，返回退出码、标准输出和错误输出。",
    "input_schema": {
        "type": "object", "properties": {}, "additionalProperties": False,
    },
}]


def ask_claude(client, model, messages):
    """只管一次 API 调用，不在这里执行工具或推进循环。"""
    response = client.messages.create(
        model=model, system=SYSTEM, messages=messages, tools=TOOLS,
        max_tokens=1024,
    )
    return response.model_dump(mode="json", exclude_none=True)


def run_main(call, workspace: Path, timeout=3):
    """固定执行当前 Python 解释器 + main.py；这是范围受限的工具，不是沙箱。"""
    result = {"type": "tool_result", "tool_use_id": call["id"]}
    if call.get("name") != "run_main" or call.get("input") != {}:
        return {**result, "content": "工具或参数不支持。", "is_error": True}
    try:
        process = subprocess.run(
            [sys.executable, "main.py"], cwd=workspace,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        output = (process.stdout + process.stderr).strip() or "（无输出）"
        return {
            **result, "content": f"exit_code={process.returncode}\n{output[:2000]}",
            "is_error": process.returncode != 0,
        }
    except subprocess.TimeoutExpired:
        return {**result, "content": f"运行超时：超过 {timeout} 秒。", "is_error": True}
    except OSError as error:
        return {**result, "content": f"无法启动：{error}", "is_error": True}


def run_loop(ask, execute, max_calls=4, emit=print):
    """ask 读完整记录，execute 读工具请求；返回状态和证据，避免把停下当作成功。"""
    if max_calls < 1:
        raise ValueError("max_calls 必须至少为 1")
    messages = [{"role": "user", "content": QUESTION}]

    def finish(status, text, calls):
        return {"status": status, "text": text, "calls": calls, "messages": messages}

    for number in range(1, max_calls + 1):
        emit(f"模型调用 {number}")
        try:
            response = ask(messages)
        except Exception as error:
            # API 异常时交回控制权；不自动重试，也不伪造工具结果。
            return finish("model_error", f"模型请求失败：{type(error).__name__}", number)
        blocks = response.get("content")
        reason = response.get("stop_reason")
        if not isinstance(blocks, list) or any(
            not isinstance(block, dict) or block.get("type") not in ("text", "tool_use")
            for block in blocks
        ):
            return finish("protocol_error", "响应不符合本课支持的格式。", number)
        messages.append({"role": "assistant", "content": blocks})
        calls = [block for block in blocks if block["type"] == "tool_use"]
        text = "\n".join(block.get("text", "") for block in blocks if block["type"] == "text")
        if reason == "end_turn" and not calls and text.strip():
            return finish("answered", text, number)
        if reason not in ("end_turn", "tool_use"):
            return finish("model_stopped", f"模型停止：{reason}；需要检查响应。", number)
        ids = [call.get("id") for call in calls]
        if reason != "tool_use" or not calls or any(
            not isinstance(call_id, str) or not call_id for call_id in ids
        ) or len(set(ids)) != len(ids):
            return finish("protocol_error", "停止原因与工具请求不一致。", number)
        # 上面已经保存完整 assistant 响应；每个结果必须关联原调用 ID。
        results = []
        for call in calls:
            emit(f"执行工具 {call.get('name')}")
            result = execute(call)
            results.append(result)
            emit("工具结果：" + result["content"].splitlines()[-1])
        messages.append({"role": "user", "content": results})
        emit("保存工具结果，供下一次调用读取")
    return finish("call_limit", f"已达 {max_calls} 次模型调用上限；保留记录，交给用户。", max_calls)
