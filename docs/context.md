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


第五课TodoWrite（2026-10-19）：s05-todo-write新增validate_todos/write_todos/prepare_messages；整份有界清单原子替换，请求副本附当前计划不改历史。s04注入guard保持默认权限，s05仅显式放行内存计划工具且保留blocked/hooks。10测试、11内存绑定、SDK两路径各8模拟HTTP，无在线模型。见implementation/s05-todo-write.md。
