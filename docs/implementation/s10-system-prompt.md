# 第十课 System Prompt（2026-10-19）

父585f41e；开始读README/AGENTS/context/examples与相关记录，先运行s09公开check入口，实际新会话读偏好、父5次并核对42，再读正式core。问题是目录与实际注册增长后，手工拼接提示容易仍声称有已关闭工具。collect_context/assemble_system_prompt/get_system_prompt逐个处理真实状态、固定/可选段与本地复用；不复制循环。

设计：同一程序核对对照允许、拒绝、只读。只读实际移除run_main，提示/tool字段/分发都沿当前注册；仅提示变化不授予执行许可，未知调用不能执行。技能加载工具关闭时不发送目录。默认无记忆，需要显式指定s09保存的项目目录；目录进入system，正文和计划仍进本次请求副本，不进缓存key。子任务system保持前课独立只读配置，本课仅重构父。

缓存单项/本进程/串行，规范化JSON基本数据+TEMPLATES实际文本；不用default=str、处理函数身份或问题关键词。输入24000字节、system12000字节；完整组装和预算通过后cache.update，返回复制。模板/描述/schema/目录/工作区变化重新组装；生成文本可能相同。不是API缓存或性能基准，不加cache_control，不减少模型调用。没有热插拔/并发注册保障。

实际验证21标准库测试、14同源教学绑定通过；SDK1.13.0模拟HTTP允许/拒绝/只读8/8/7次通过，包含system/tools一致、内存复用后仍发请求、父记忆正文隔离、子不继承、真实进程许可/未知调用、缓存失败保留旧值、返回副本与完整输出多一行反例。主/子默认固定响应，文件/目录/获准进程真实执行；未调用在线模型。绑定临时目录真实、工具函数仅作为注册数据不执行、预热使用同源原函数，准备区公开。

资料https://learn.shareai.run/zh/s10/、https://platform.claude.com/docs/en/build-with-claude/prompt-caching、https://code.claude.com/docs/en/how-claude-code-works，访问2026-10-19。只以官方说明界定API缓存与文字配置，社区不可核验的Claude Code内部源码分析不作为实现事实；本例不复现官方system prompt。
