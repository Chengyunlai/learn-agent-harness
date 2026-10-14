# 项目上下文

公开 Python 教学仓库 `Chengyunlai/learn-agent-harness`，配套小册 `/zh/books/learn-claude-code`。站点保存文章和 SVG/代码块交互；独立仓库提供读者可克隆的实践实现。

第一课在 `examples/s01-agent-loop/`：`user_code/practice.py` 默认离线模型替身，真实执行本课 workspace/main.py；--live 使用官方 Anthropic Python SDK。`core/runtime.py` 是唯一实现，ask_claude 负责一次 API，run_main 执行固定文件，run_loop 保存完整请求/关联结果并限制调用次数。

Python3.10+，默认入口/verify_practice 仅标准库。requirements.txt 固定anthropic1.13.0；verify_sdk 使用依赖自带httpx2.MockTransport，HTTP全部模拟，无在线模型调用。默认4次模型调用、3秒进程超时、20秒网络超时；SDK不自动重试。answered与程序成功分离；记录只在进程内存中。

先读 [examples](../examples/README.md)，运行入口后读 [core 映射](../examples/s01-agent-loop/core/README.md)。设计、迁移来源和实际验证见 [第一课记录](implementation/s01-agent-loop.md)。后续课程在同一项目扩展，保持每课入口可运行，不提前增加权限、恢复、并发等生产架构。


实践文章现在用三个完整函数的断点轨迹驱动SVG，代码与图宽屏同一行，站点复用PythonDemo/PythonFigure。user_code/figure_fixtures.py的fixture_context按函数与场景提供setup/entry/watch/scopes；SDK/进程替身明确标注，正式函数body保持原样，循环所需两个helper按inspect.getsource取自core，未另写循环。verify_fixtures.py验证八组输入，不访问API或真实文件进程；原verify_practice/SDK模拟HTTP继续验证实际入口。站点只生成源码摘录与教学绑定，不维护另一个Python实践实现。reading_demo/verify_reading保留作既有短代码实验，已不作为三个函数的替代展示。CI的3.10/3.13增加fixture验证。

2026-10-14：配套小册展示名改为《Agent 与 Harness：思想与 Python 实践》，README链接名称同步，原URL/项目路径/运行时不变。Learn Claude Code为课程参考来源，Python实现由本项目独立维护。
