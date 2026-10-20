# Learn Agent Harness

用 Python 逐课理解和编写 Agent Harness。配套小册：[Agent 与 Harness：思想与 Python 实践](https://www.chengyunlai.top/zh/books/learn-claude-code)。

每课围绕一个具体问题，只增加当前机制需要的实现。先运行 `user_code/`，再沿 `core/` 中的函数读代码。当前已提供第一课 Agent Loop、第二课 Tool Use 与第三课 Permission。

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
处理工具请求 run_main
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

## 第二课：工具分发

```bash
python3 examples/s02-tool-use/user_code/practice.py
python3 examples/s02-tool-use/user_code/verify_practice.py
python3 examples/s02-tool-use/user_code/verify_fixtures.py
```

先读main.py，再运行取得42，三次离线判断后回答；文件与进程真实执行。注册表同时保存说明、参数与实现，循环复用第一课。6组标准库测试与8组浏览器教学输入；可选SDK模拟HTTP验证入口verify_sdk.py。完整边界与文章链接见[第二课](examples/s02-tool-use/README.md)。

## 第三课：执行之前取得权限

```bash
python3 examples/s03-permission/user_code/practice.py --decision deny
python3 examples/s03-permission/user_code/practice.py --decision allow
python3 examples/s03-permission/user_code/verify_practice.py
```

同一请求按宿主规则/回答决定是否执行；9组真实程序测试与13组浏览器输入，SDK模拟HTTP对照允许/拒绝。默认ask仅在交互终端询问，非交互拒绝。细节与文章见[第三课](examples/s03-permission/README.md)。

## 第四课 Hooks

[公开入口与说明](examples/s04-hooks/README.md)：在原权限入口前后增加同步检查与审计，故障按发生时机处理。`python3 examples/s04-hooks/user_code/practice.py --decision allow --audit-failure`可对照实际结果和宿主警告。


第五课[TodoWrite](examples/s05-todo-write/README.md)：`python3 examples/s05-todo-write/user_code/practice.py --decision allow`。内存计划原子替换，每轮读取当前清单，状态与真实执行分开验证。


第六课[Subagent](examples/s06-subagent/README.md)：独立消息、只读工具、同步有界子循环；父循环只接收状态和短结论。入口`python3 examples/s06-subagent/user_code/practice.py --decision deny`，设计与验证见`docs/implementation/s06-subagent.md`。


第七课[Skills](examples/s07-skills/README.md)：启动读取技能头部，system只带目录，load_skill按注册名称读取完整有界正文。入口`python3 examples/s07-skills/user_code/practice.py --decision deny`，保留前课清单/Hook/权限/子任务，正文不授予权限。


第八课[Context Compact](examples/s08-context-compact/README.md)：按完整交接分组，先保存压缩前快照，再移出旧工具正文，仍超预算才摘要旧前缀。原run_loop新增可选prepare候选提交入口，失败context_error保留旧历史；默认行为不变。


第九课[Memory](examples/s09-memory/README.md)：`remember --approve`经宿主确认将稳定偏好保存到项目JSON；新`check`会话生成元数据目录、关键词选择、正文附请求副本。记忆不授予运行许可，当前文件证据与原循环保持独立。


第十课[System Prompt](examples/s10-system-prompt/README.md)：从实际注册/目录收集快照，固定顺序分段组装，校验与预算通过才更新本地单项缓存；只读模式实际移除run_main。入口practice.py --read-only；本地复用仍会发模型请求，不是API提示缓存。


第十一课[Error Recovery](examples/s11-error-recovery/README.md)：只包装父模型请求，分类/退避/有界恢复，完整响应才交回原循环；已有工具结果保留，截断请求不执行。每轮4次、父会话20次尝试/3秒计划等待，源码与证据见docs/implementation/s11-error-recovery.md。


第十二课[Task System](examples/s12-task-system/README.md)：单写者持久任务图，依赖检查/宿主认领/完成与解锁，跨进程恢复进度；任务状态不代替执行证据。公开入口init/show/work，设计与验证见docs/implementation/s12-task-system.md。


第十三课[Background Tasks](examples/s13-background-tasks/README.md)：固定main.py显式后台启动，收据/进程结果/文本通知分别交接；轮次边界非阻塞检查，模型先停时由宿主回收并展示未消费结果，无忙等模型调用。


第十四课[Cron Scheduler](examples/s14-cron-scheduler/README.md)：时间匹配、触发入队、空闲交付；固定UTC+08:00会话内表，执行权限独立，默认注入时钟，--serve-seconds才运行本进程调度线程。


第十五课[Agent Teams](examples/s15-agent-teams/README.md)：独立成员上下文与追加式JSONL收件箱，reader接收reviewer信息后沿用原调查，queued和模型已读分开；12测试/18输入/SDK模拟HTTP。


第十六课[Team Protocols](examples/s16-team-protocols/README.md)：类型化计划与关闭协议，保存/匹配分开；ID、角色、重复决定与空闲确认，协作门控与宿主执行许可独立。11测试/22输入/SDK三路径各8模拟HTTP。


第十七课[Autonomous Agents](examples/s17-autonomous-agents/README.md)：空闲查板、自主认领与锁内重检，依赖解锁后再取任务，关闭优先/锁外等待/有界停止；13测试、22输入、SDK三路径各8模拟HTTP。

第十八课[Worktree Isolation](examples/s18-worktree-isolation/README.md)：两个队友各改自己的main.py；创建/owner绑定/保留清理三个函数，真实Git双线程、14测试/19教学输入，SDK两路径各7模拟HTTP；没有自动合并或沙箱。

第十九课[MCP Tools](examples/s19-mcp-tools/README.md)：发现完整目录、统一模型定义与路由、宿主确认后调用；12标准库测试/21教学输入，官方MCP1.26.0真实stdio与2025-11-25协商，Anthropic模拟HTTP5/4次，无在线模型。

第二十课[Comprehensive Agent Turn](examples/s20-comprehensive-agent/README.md)：请求准备、同一能力快照分发、有限循环与收尾；14标准库测试/18同源输入，真实MCP/文件/归档/进程与模拟HTTP6/5次，无在线模型。
