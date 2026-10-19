# 2026-10-19：第五课 TodoWrite

基于父091bec4。新增原子整份替换内存计划，状态是模型声明，不能证明执行。三关键函数validate_todos/write_todos/prepare_messages。首条问题副本附带当前计划，原循环/原历史不变，不堆叠提醒。读取源码/预期/真实运行为贯穿案例，许可拒绝保留未完成项。

s04 execute_hooked增加可选guard参数（默认原execute_guarded），仅将已有执行依赖变成可注入；s05显式允许本地todo_write，不取消blocked/before，其他工具仍s03权限。s02原生成器只支持string，新课独立生成todo数组schema，不改变前课契约。Hook与原权限回归11测试/12绑定通过。

10组标准库测试含晚项失败原子性、字段/状态/ID/上限、提交副本、清空/省略删除、全completed不运行、请求副本不累计、非法调用协议ID/审计/不询问、todo禁止项、真实allow/deny/maintenance与预算。11纯内存绑定原样函数正文。固定SDK1.13.0两条路径各8次模拟HTTP，数组schema/原问题/当前计划/运行ID/真实标记通过。公开入口先运行后阅读core，无在线模型运行。索引/context/README/CI同次更新。

离线响应的输出核对比较完整输出正文，不能只比较最后一行；新增多一行输出的反例，验证不会误报一致。标准库测试现11组。核心计划函数与绑定不变。
