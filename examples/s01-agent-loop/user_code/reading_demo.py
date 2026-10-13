max_calls = 4
truncated = False


def ask(messages):
    # 固定响应替代模型；保留 stop_reason 和内容块结构。
    if truncated:
        return {"stop_reason": "max_tokens", "content": []}
    if len(messages) == 1:
        call = {"type": "tool_use", "id": "call_1", "name": "run_main", "input": {}}
        return {"stop_reason": "tool_use", "content": [call]}
    text = {"type": "text", "text": "运行失败：除零错误"}
    return {"stop_reason": "end_turn", "content": [text]}


def execute(call):
    # 直接求值替代文件进程；真实触发并捕获异常。
    try:
        10 / 0
    except ZeroDivisionError as error:
        return {"tool_use_id": call["id"], "is_error": True,
                "content": f"{type(error).__name__}: {error}", "type": "tool_result"}


messages = [{"role": "user", "content": "运行 main.py，只报告结果。"}]
for number in range(1, max_calls + 1):
    response = ask(messages)
    messages.append({"role": "assistant", "content": response["content"]})
    if response["stop_reason"] == "end_turn":
        print("answered：", response["content"][0]["text"])
        break
    if response["stop_reason"] != "tool_use":
        print("model_stopped：", response["stop_reason"])
        break
    result = execute(response["content"][0])
    messages.append({"role": "user", "content": [result]})
    print("保存", result["tool_use_id"], "；记录", len(messages))
else:
    print("call_limit：", number, "次调用；结果已保存")
