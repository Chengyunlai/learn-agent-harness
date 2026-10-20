# 第十九课设计与证据（2026-10-20）

编辑卡：已有本地工具/许可/Hook/能力缓存/唯一循环；问题是外部服务如何提供可发现的工具而无需把业务实现复制进Harness。贯穿docs搜索运行许可→读本地策略→报告对照。先用公开s18入口验证旧链，再编写MCP桥；不假装覆盖所有schema/传输。Python3.10+，本机实际SDK运行3.14.6，MCP1.26.0、Anthropic1.13.0，协议协商2025-11-25。

来源2026-10-20：https://learn.shareai.run/zh/s19/作学习方向；https://modelcontextprotocol.io/specification/2025-11-25/server/tools支持分页/输入/调用/错误/不信任annotations；https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle支持初始化/能力/关闭/超时；官方Python SDK v1.26.0源码与实际安装核对ClientSession/Server API。不采信参考所谓Claude内部代码行号、其删除缓存或readOnly即许可等推断。

三个核心函数同步并可绑定浏览器；官方SDK session在async loop，旧同步run_loop由to_thread运行，bridge投回loop。完整发现后候选组装成功才发布；模型工具名和原服务名由route显式映射，冲突拒绝；输入/许可/结果/调用ID关联，无工具重试。单会话串行更新，无并发热刷新或重连/OAuth。每页24000字节、4页8工具、2服务、4短字符串参数/120字符、纯文本4块2000字符；特意不支持的schema/内容拒绝。目录描述不授予许可，readOnlyHint不信任。

11标准库测试/21绑定通过；官方SDK真实stdio允许/默认拒绝/业务错误/坏schema四路径为4/3/3/2逻辑请求，服务调用1/0/1/0次。一次真实调用已由server记录但等待超时，保留关联错误且不重发。Anthropic MockTransport允许/拒绝各5/4HTTP含工具反馈后529，MCP仍1/0次，新增工具system缓存失效、同配置复用。初始化、服务业务逻辑、本地文件均真实，无在线模型或外部业务系统；浏览器分页/调用明确内存替身。Git父c419125，后续提交固定站内摘录版本。
