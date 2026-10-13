# 项目上下文

公开 Python 教学仓库 `Chengyunlai/learn-agent-harness`，配套小册 `/zh/books/learn-claude-code`。站点保存文章和 SVG/代码块交互；独立仓库提供读者可克隆的实践实现。

第一课在 `examples/s01-agent-loop/`：`user_code/practice.py` 默认离线模型替身，真实执行本课 workspace/main.py；--live 使用官方 Anthropic Python SDK。`core/runtime.py` 是唯一实现，ask_claude 负责一次 API，run_main 执行固定文件，run_loop 保存完整请求/关联结果并限制调用次数。

Python3.10+，默认入口/verify_practice 仅标准库。requirements.txt 固定anthropic1.13.0；verify_sdk 使用依赖自带httpx2.MockTransport，HTTP全部模拟，无在线模型调用。默认4次模型调用、3秒进程超时、20秒网络超时；SDK不自动重试。answered与程序成功分离；记录只在进程内存中。

先读 [examples](../examples/README.md)，运行入口后读 [core 映射](../examples/s01-agent-loop/core/README.md)。设计、迁移来源和实际验证见 [第一课记录](implementation/s01-agent-loop.md)。后续课程在同一项目扩展，保持每课入口可运行，不提前增加权限、恢复、并发等生产架构。
