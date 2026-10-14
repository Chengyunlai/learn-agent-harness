# Learn Agent Harness

用 Python 逐课理解和编写 Agent Harness。配套小册：[Agent 与 Harness：思想与 Python 实践](https://www.chengyunlai.top/zh/books/learn-claude-code)。

每课围绕一个具体问题，只增加当前机制需要的实现。先运行 `user_code/`，再沿 `core/` 中的函数读代码。当前已提供第一课 Agent Loop，后续课程在同一仓库逐步扩展。

## 第一课：先运行一次

Python 3.10+；默认入口只用标准库，无需 API Key：

```bash
git clone https://github.com/Chengyunlai/learn-agent-harness.git
cd learn-agent-harness
python3 examples/s01-agent-loop/user_code/practice.py
```

用户问题是“运行 main.py，只报告结果。”默认文件包含 `print(10 / 0)`。入口使用固定模型响应，真实启动 Python 进程，取得错误后保存，再进行第二次离线判断：

```text
离线模式：模型响应为测试替身，main.py 真实执行
模型调用 1
执行工具 run_main
工具结果：ZeroDivisionError: division by zero
保存工具结果，供下一次调用读取
模型调用 2
停止状态：answered
运行失败：除零错误
```

`answered` 表示收到了回答，不代表程序运行成功。用 `--max-calls 1` 可以观察保存结果后以 `call_limit` 停止；CLI 此时退出码为 1。用 `--workspace` 可以指定一个教学文件目录。

阅读配对文章：[思想｜一句请求怎样变成执行结果](https://www.chengyunlai.top/zh/blog/learn-claude-code-agent-loop)、[实践｜写出第一个可控的循环](https://www.chengyunlai.top/zh/blog/learn-claude-code-agent-loop-practice)。

## 验证

标准库测试运行真实成功、除零和超时进程，检查记录关联与停止边界：

```bash
python3 examples/s01-agent-loop/user_code/verify_practice.py
python3 examples/s01-agent-loop/user_code/verify_reading.py
python3 examples/s01-agent-loop/user_code/verify_fixtures.py
```

可选 SDK 验证：安装固定版本后，以模拟 HTTP 验证真实 SDK 的报文转换，不访问模型服务。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python examples/s01-agent-loop/user_code/verify_sdk.py
```

实践文章逐个展开完整函数，复用代码块的真实断点轨迹驱动SVG。`user_code/figure_fixtures.py`提供八组浏览器教学输入；三个正式函数正文原样执行，API/进程使用替身，不访问在线服务、不启动文件。`verify_fixtures.py`验证这些输入与返回，正式实践入口仍启动真实进程。

早期短代码`user_code/reading_demo.py` 是浏览器短代码的公开原文件：固定模型响应保留停止原因、消息块和调用ID，直接求值替代文件进程；只验证教学机制。`verify_reading.py` 用真实行前快照检查保存前后、两次判断、调用上限和截断不执行。

已验证 9 项标准库测试、真实 Python 进程、Anthropic Python SDK 1.13.0 的模拟 HTTP 请求/响应；尚未调用在线模型。GitHub Actions 分别运行 Python 3.10/3.13 的离线入口和测试，以及 Python 3.13 的 SDK 验证。

## 可选：真实模型

在自己的终端配置 `ANTHROPIC_API_KEY` 与 `ANTHROPIC_MODEL` 环境变量，模型名称使用账户可用、支持工具调用的型号。只有显式加上 `--live` 才发出 API 请求：

```bash
.venv/bin/python examples/s01-agent-loop/user_code/practice.py --live
```

默认最多 4 次模型调用，SDK 自动重试关闭，网络超时 20 秒，文件执行超时 3 秒。固定工具只运行工作目录的 main.py，文件仍以本机权限执行；这是教学入口，不是代码执行沙箱。只用可信的短教学文件；输出截取 2000 字符不等于进程输出内存或进程树资源限制。

## 代码位置

```text
examples/
└── s01-agent-loop/
    ├── user_code/
    │   ├── practice.py          # 离线 / 在线运行入口
    │   ├── verify_practice.py   # 标准库验证
    │   ├── verify_sdk.py        # SDK + 模拟 HTTP
    │   └── workspace/main.py    # 本课教学文件
    └── core/runtime.py          # 模型调用 → 工具执行 → 有限循环
requirements.txt                # 可选 SDK 依赖
```

从 [examples 索引](examples/README.md)到 [core 符号映射](examples/s01-agent-loop/core/README.md)，按 `ask_claude → run_main → run_loop` 阅读。设计和证据见 [项目上下文](docs/context.md)与 [第一课记录](docs/implementation/s01-agent-loop.md)。

本仓库是配套教学实现，参考 [Learn Claude Code](https://github.com/shareAI-lab/learn-claude-code) 的最小循环思想，并按本课范围增加停止控制；不代表 Claude Code 的完整运行时。

License: [MIT](LICENSE)。
