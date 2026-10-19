# 第八课实现记录（2026-10-19）

编辑卡：已理解Skills与独立上下文的Python读者；问题是加载/文件反馈仍累积。沿main.py/expected/许可，增加4份教学旧日志触发容量压力。认知路线：活跃历史与归档分开→完整工具交接边界→便宜地移出旧正文→仍超预算才摘要→候选验证后提交。参考课程s08与官方https://code.claude.com/docs/en/how-claude-code-works、https://platform.claude.com/docs/en/build-with-claude/compaction，核于2026-10-19；本例普通Messages摘要，不推断产品内部实现、不实现服务端API。

三个函数split_history/trim_results/prepare_context。请求前整理，仅支持本例user文本+完整工具组；至少保留近期1组，原问题外置固定、当前计划与权限由宿主持有。压缩前快照先写，旧大正文移出再做必要摘要；摘要失败/预算用尽/近期单组过大保留原历史并context_error。字节阈值不等于token窗口，system/tools/计划不计入。没有应急无限重试、全量对话恢复、自动执行归档命令或模型归档检索。

s01 run_loop新增prepare=None，缺省完全保留旧行为；传入时深副本预处理、成功才提交，失败calls计前面已发父请求。此公开API变更同步总索引/context/core映射。前七课verify_practice/verify_fixtures全回归通过。

s08实际34断言、14绑定/187正式trace帧，验证快照JSONL与输入相等、近期不可拆、ID/is_error保留、摘要/归档失败不提交、坏摘要/预算、外部计划回填、恶意旧允许不变成新许可、真实程序标记与完整输出反例。固定SDK1.13.0允许/拒绝各13模拟HTTP（父9/子3/摘要1）及截断摘要拒收，无在线调用。摘要计单独尝试预算2，不自动重试。此提交为站点固定源码与绑定的公开源版本；站点另记文章/图和浏览器交付关系。
