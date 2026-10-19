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
| 浏览器教学短代码与行前快照验证 | `../user_code/reading_demo.py`、`verify_reading.py` |
| 函数图的可查看教学绑定 | `../user_code/figure_fixtures.py`：`fixture_context`；`verify_fixtures.py`原样执行core函数 |
| SDK + 模拟HTTP请求/响应 | `../user_code/verify_sdk.py`：`respond` |

run_main为空参数自定义客户端工具，不是通用bash工具或隔离沙箱。完整有效assistant内容保存后再执行；结果以user/tool_result消息回传。正常回答、调用上限、API异常、响应截断和协议矛盾分别返回，进程错误作为工具反馈。

第八课新增run_loop(...,prepare=None)：可选请求前候选处理，深副本运行、成功才提交；失败context_error，calls仍只计已发送父请求。默认None不改变第一课行为。
