# 实践 Examples

在仓库根目录运行，先 user_code，再 core。

| 课 | 问题与运行入口 | 核心实现 | 验证 |
| --- | --- | --- | --- |
| [第一课：Agent Loop](s01-agent-loop/README.md) | `python3 examples/s01-agent-loop/user_code/practice.py`：运行 main.py，只报告结果 | `core/runtime.py`：模型调用、固定工具、记录关联、有限循环 | `verify_practice.py` 真实进程；`figure_fixtures.py` / `verify_fixtures.py`三个原样函数八组教学输入；reading_demo保留；`verify_sdk.py` SDK模拟HTTP |
| [第二课：Tool Use](s02-tool-use/README.md) | `python3 examples/s02-tool-use/user_code/practice.py`：先读文件，再运行 | 注册/分发/有限读取；复用第一课循环 | verify_practice、verify_fixtures、verify_sdk |

| [第三课：Permission](s03-permission/README.md) | `python3 examples/s03-permission/user_code/practice.py --decision deny` / `--decision allow` | 策略/宿主确认/执行快照；复用第二课和循环 | 9组真实执行测试、13输入、SDK模拟HTTP |

第二课新增两项工具的注册、分发与路径读取，复用第一课循环。后续按实际实现追加，不发布空目录。

第四课[Hooks](s04-hooks/README.md)：`python3 examples/s04-hooks/user_code/practice.py --decision allow`，增加--maintenance或--audit-failure观察阻止与警告；core三个函数，11测试/12绑定/SDK模拟HTTP。


第五课[TodoWrite](s05-todo-write/README.md)：实践入口--decision allow/deny，--maintenance或--max-calls 4触发边界。三个计划函数、11测试/11教学输入/SDK模拟HTTP。


第六课[Subagent](s06-subagent/README.md)：独立消息、只读工具、同步有界子循环；父循环只接收状态和短结论。入口`python3 examples/s06-subagent/user_code/practice.py --decision deny`，设计与验证见`docs/implementation/s06-subagent.md`。


第七课[Skills](s07-skills/README.md)：启动读取技能头部，system只带目录，load_skill按注册名称读取完整有界正文。入口`python3 examples/s07-skills/user_code/practice.py --decision deny`，保留前课清单/Hook/权限/子任务，正文不授予权限。
