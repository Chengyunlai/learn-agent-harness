# 正式符号映射

| 符号 | 职责与旧实现 |
| --- | --- |
| prepare_turn | 压缩候选history、请求messages、非破坏通知；s08/s09由宿主传入 |
| dispatch_call | 同一响应能力快照→s04 Hook→s19外部或s07技能/s03本地许可 |
| run_session | s01唯一run_loop的prepare/ask/execute三回调，s11请求恢复和finally收尾 |
| freeze_capabilities | 冻结元数据，保留宿主连接/可调用对象 |
| user_code.practice.run_example | s07规范、s09记忆、s08真实归档、s10系统缓存与证据核对 |
| user_code.practice.real_mcp | 官方MCP初始化、s19适配器、异步上下文关闭 |

断点按符号，不依赖行号。先user_code入口，core实现只有本阶段装配职责；旧机制从各自examples导入。
