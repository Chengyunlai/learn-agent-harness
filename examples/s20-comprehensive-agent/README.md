# 第二十课：Comprehensive Agent Turn

Python3.10+。先运行user_code公开入口，再按core符号看源码。

```bash
python3 examples/s20-comprehensive-agent/user_code/practice.py --decision allow
python3 examples/s20-comprehensive-agent/user_code/practice.py
python3 examples/s20-comprehensive-agent/user_code/practice.py --decision allow --max-calls 4
python3 examples/s20-comprehensive-agent/user_code/practice.py --decision allow --mode mismatch
python3 examples/s20-comprehensive-agent/user_code/verify_practice.py
python3 examples/s20-comprehensive-agent/user_code/verify_fixtures.py
# 可选真实官方MCP与模拟Anthropic HTTP：
python3 -m pip install -r requirements.txt -r examples/s19-mcp-tools/requirements.txt
python3 examples/s20-comprehensive-agent/user_code/practice.py --mcp --decision allow
python3 examples/s20-comprehensive-agent/user_code/verify_sdk.py
```

默认固定模型、显式LocalDocs内存替身，真实技能/记忆文件、源码读取、压缩快照落盘与获准main.py进程；--mcp用官方mcp1.26.0 ClientSession和s19自有server.py真实stdio。Anthropic1.13.0验证用MockTransport，无在线模型/外部业务服务。所有文件在临时目录，退出整体删除；不是任意代码沙箱。五次逻辑模型调用：规范→源码→外部规则→运行→回答；默认拒绝外部查询，四次回答但verified=false；上限四次可实际运行成功却call_limit。固定模型只验证调度，不证明模型规划/文本推理质量。

prepare_turn压缩canonical候选，记忆/非破坏读取通知只在请求副本；失败原历史不变。通知上限4×240字符，最终消息8000UTF8字节；compaction归档/额度等外部状态不会随候选失败回滚。示例通知为空，不编造后台完成。s08只处理完整工具交接，因此s13/s15通知不直接塞进其canonical历史；跨轮事件确认/去重需宿主账本，本课不自动drain。

dispatch_call共用s04前后Hook；外部路由s19独立许可，load_skill按s07显式只读入口，其余s03默认拒绝策略。freeze_capabilities复制定义、路由元数据与本地注册，保留宿主可调用对象；单会话串行，无热撤销/并发注册。run_session只装配原唯一run_loop：prepare提交canonical；ask使用请求副本与该响应冻结的能力；s11只包send，最多20实际请求/3秒计划等待、每逻辑4尝试；循环1..8逻辑调用，默认5。finally执行一次宿主收尾，不调用模型，不把收尾警告覆盖原停止原因。非预期工具边界异常为host_error，messages/calls为None，不声称保存了无法取出的内部历史；审计另由宿主持有。参数校验在接管close前，非法max_calls由外层资源上下文负责关闭。

模型answered只表示产生合法文本；verified独立核对实际run_main审计结果exit_code=0/42。示例没有队友、后台、cron、修改或worktree需求，按入口分层而非给每次ask挂全部机制：s12/s14/s17决定交付哪项用户任务；s15/s16/s18决定成员/目录/关闭；本课负责一次已交付任务。没有第二条Agent循环、自动排新任务、重启恢复、事务承诺或收尾时等所有后台工作。

14标准库测试、18同源教学输入。SDK验证允许6/拒绝5模拟HTTP，含已有工具结果后529；真实MCP调用1/0、实际run_main1/0，重试请求相同，收尾一次。浏览器原函数/原循环/原恢复/Hook/权限真实运行；模型、文件进程、压缩/附件和连接接口为公开内存教学绑定。
