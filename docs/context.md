# 项目上下文

公开 Python 教学仓库 `Chengyunlai/learn-agent-harness`，配套小册 `/zh/books/learn-claude-code`。站点保存文章和 SVG/代码块交互；独立仓库提供读者可克隆的实践实现。

第一课在 `examples/s01-agent-loop/`：`user_code/practice.py` 默认离线模型替身，真实执行本课 workspace/main.py；--live 使用官方 Anthropic Python SDK。`core/runtime.py` 是唯一实现，ask_claude 负责一次 API，run_main 执行固定文件，run_loop 保存完整请求/关联结果并限制调用次数。

Python3.10+，默认入口/verify_practice 仅标准库。requirements.txt 固定anthropic1.13.0；verify_sdk 使用依赖自带httpx2.MockTransport，HTTP全部模拟，无在线模型调用。默认4次模型调用、3秒进程超时、20秒网络超时；SDK不自动重试。answered与程序成功分离；记录只在进程内存中。

先读 [examples](../examples/README.md)，运行入口后读 [core 映射](../examples/s01-agent-loop/core/README.md)。设计、迁移来源和实际验证见 [第一课记录](implementation/s01-agent-loop.md)。后续课程在同一项目扩展，保持每课入口可运行，不提前增加权限、恢复、并发等生产架构。


实践文章现在用三个完整函数的断点轨迹驱动SVG，代码与图宽屏同一行，站点复用PythonDemo/PythonFigure。user_code/figure_fixtures.py的fixture_context按函数与场景提供setup/entry/watch/scopes；SDK/进程替身明确标注，正式函数body保持原样，循环所需两个helper按inspect.getsource取自core，未另写循环。verify_fixtures.py验证八组输入，不访问API或真实文件进程；原verify_practice/SDK模拟HTTP继续验证实际入口。站点只生成源码摘录与教学绑定，不维护另一个Python实践实现。reading_demo/verify_reading保留作既有短代码实验，已不作为三个函数的替代展示。CI的3.10/3.13增加fixture验证。

2026-10-14：配套小册展示名改为《Agent 与 Harness：思想与 Python 实践》，README链接名称同步，原URL/项目路径/运行时不变。Learn Claude Code为课程参考来源，Python实现由本项目独立维护。

第二课Tool Use（2026-10-16）在examples/s02-tool-use：build_tools以同一注册派生模型定义与本地调用，execute_tool校验名称/字段/类型并保留调用ID，read_file约束解析目录与4096字节UTF-8。循环与进程按文件路径加载第一课唯一实现；run_loop仅新增question可选参数，旧默认不变。默认离线模型+真实文件/进程；浏览器3函数8输入使用公开文件/进程替身；verify_sdk为固定SDK模拟HTTP。索引、符号、测试和配套文章同步，记录见implementation/s02-tool-use.md。

第三课Permission（2026-10-18）：s03-permission的permission_for只做策略判断，authorize_call在ask时获取宿主bool回答，execute_guarded以同一调用副本授权/执行。blocked优先、无策略拒绝、拒绝回传未执行结果；复用第二课提取的validate_call和分发/原循环。原日志改为“处理工具请求”，避免把进入权限判断误作进程执行。默认离线模型与真实读/获准后进程；13浏览器输入使用宿主/文件/进程替身。9组真实标记测试、两条SDK模拟HTTP路径；在线模型未调用。记录implementation/s03-permission.md。

第四课Hooks（2026-10-18）：s04-hooks提供run_hooks/execute_hooked/audit_event；before顺序阻止、after警告继续，仍强制经过s03权限。审计记录在内存，warnings由装配层保留，原循环只收result。11真实程序测试、12教学输入、SDK模拟HTTP对照；无在线模型。记录implementation/s04-hooks.md。


第五课TodoWrite（2026-10-19）：s05-todo-write新增validate_todos/write_todos/prepare_messages；整份有界清单原子替换，请求副本附当前计划不改历史。s04注入guard保持默认权限，s05仅显式放行内存计划工具且保留blocked/hooks。11测试、11内存绑定、SDK两路径各8模拟HTTP，无在线模型。见implementation/s05-todo-write.md。


第六课[Subagent](../examples/s06-subagent/README.md)：独立消息、只读工具、同步有界子循环；父循环只接收状态和短结论。入口`python3 examples/s06-subagent/user_code/practice.py --decision deny`，设计与验证见`docs/implementation/s06-subagent.md`。


第七课[Skills](../examples/s07-skills/README.md)：启动读取技能头部，system只带目录，load_skill按注册名称读取完整有界正文。入口`python3 examples/s07-skills/user_code/practice.py --decision deny`，保留前课清单/Hook/权限/子任务，正文不授予权限。


第八课[Context Compact](../examples/s08-context-compact/README.md)：按完整交接分组，先保存压缩前快照，再移出旧工具正文，仍超预算才摘要旧前缀。原run_loop新增可选prepare候选提交入口，失败context_error保留旧历史；默认行为不变。


第九课[Memory](../examples/s09-memory/README.md)：`remember --approve`经宿主确认将稳定偏好保存到项目JSON；新`check`会话生成元数据目录、关键词选择、正文附请求副本。记忆不授予运行许可，当前文件证据与原循环保持独立。


第十课[System Prompt](../examples/s10-system-prompt/README.md)：从实际注册/目录收集快照，固定顺序分段组装，校验与预算通过才更新本地单项缓存；只读模式实际移除run_main。入口practice.py --read-only；本地复用仍会发模型请求，不是API提示缓存。


第十一课[Error Recovery](../examples/s11-error-recovery/README.md)：只包装父模型请求，分类/退避/有界恢复，完整响应才交回原循环；已有工具结果保留，截断请求不执行。每轮4次、父会话20次尝试/3秒计划等待，源码与证据见docs/implementation/s11-error-recovery.md。


第十二课[Task System](../examples/s12-task-system/README.md)：单写者持久任务图，依赖检查/宿主认领/完成与解锁，跨进程恢复进度；任务状态不代替执行证据。公开入口init/show/work，设计与验证见docs/implementation/s12-task-system.md。
