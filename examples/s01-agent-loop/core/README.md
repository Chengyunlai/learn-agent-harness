# 正式实现映射

先运行 `../user_code/practice.py`，再按符号读 `runtime.py`。

| 阅读目标 | 符号 |
| --- | --- |
| 问题、工作约定、工具说明 | `QUESTION`、`SYSTEM`、`TOOLS` |
| 一次 API 调用与响应字典 | `ask_claude` |
| 固定文件运行、退出码、错误与超时 | `run_main` |
| 保存完整请求、tool_use_id关联、有限调用与停止状态 | `run_loop` |
| 离线/在线模式与工作目录 | `../user_code/practice.py`：`main`、`scripted_model` |
| 真实进程与循环边界 | `../user_code/verify_practice.py`：`LoopChecks` |
| SDK + 模拟HTTP请求/响应 | `../user_code/verify_sdk.py`：`respond` |

run_main为空参数自定义客户端工具，不是通用bash工具或隔离沙箱。完整有效assistant内容保存后再执行；结果以user/tool_result消息回传。正常回答、调用上限、API异常、响应截断和协议矛盾分别返回，进程错误作为工具反馈。
