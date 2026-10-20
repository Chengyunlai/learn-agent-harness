# 第二十课设计与证据（2026-10-20）

读者已掌握19种机制，当前问题是边界接错会导致附件污染/重试工具/停止误判。贯穿按项目规范读main.py→查docs许可→获准运行→核对42。先运行s19真实MCP入口。学习方向https://learn.shareai.run/zh/s20/（2026-10-20），采用边界组合思想，不复制27工具大运行时，不采信其所谓Claude内部源码。MCP规范/官方SDK同s19固定版本，独立原创装配。

三个函数prepare_turn/dispatch_call/run_session；保留唯一旧run_loop，不把teams/cron/worktree强塞无需求任务。canonical与request副本区分；非破坏通知附请求，不破坏s08完整交接契约；无事件确认事务。冻结定义/route元数据，保留连接；Hook包外部/技能/本地许可。恢复只包send；finally一次，收尾异常作警告，host_error不假称取出内部历史。验收源码/公开绑定/测试与版本关系写入本站记录。

14标准库回归、18同源输入；官方MCP1.26.0真实stdio及Anthropic1.13.0模拟HTTP6/5请求（含tool_result后的529），服务1/0调用、真实main.py1/0运行；无在线模型。压缩实际归档、技能/记忆实际文件。默认显式LocalDocs替身与--mcp区别。模型answered与verified分开，上限4次实际输出正确仍call_limit；收尾故障不覆盖answered。Git父ecef684，后续固定提交供本站摘录。
