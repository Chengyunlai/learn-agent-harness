# 正式符号映射

先运行../user_code/practice.py，断点按符号。

| 符号 | 交接职责 |
| --- | --- |
| discover_tools | 分页→验证→完整目录，失败不发布部分结果 |
| assemble_tool_pool | 内置定义+外部目录→同一份definitions/routes |
| call_external | 模型调用ID→路由/参数/宿主许可→MCP原名→关联结果 |
| checked_tool / result_text | 本课明确支持的schema/结果子集 |
| user_code.practice.SessionBridge | 旧同步循环工作线程→创建session的异步loop |
| user_code.practice.run_example | 动态池发布、真实能力system缓存、原循环/Hook/宿主决定 |
| user_code.practice.demo / server | 官方SDK真实stdio生命周期/能力/本地服务 |

运行时复用s18链上的旧循环、s10系统说明与s11请求恢复；MCP工具不重试。前课任务/工作目录保持独立，本课聚焦外部工具桥接，无第二条Agent循环。
