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


第八课[Context Compact](s08-context-compact/README.md)：按完整交接分组，先保存压缩前快照，再移出旧工具正文，仍超预算才摘要旧前缀。原run_loop新增可选prepare候选提交入口，失败context_error保留旧历史；默认行为不变。


第九课[Memory](s09-memory/README.md)：`remember --approve`经宿主确认将稳定偏好保存到项目JSON；新`check`会话生成元数据目录、关键词选择、正文附请求副本。记忆不授予运行许可，当前文件证据与原循环保持独立。


第十课[System Prompt](s10-system-prompt/README.md)：从实际注册/目录收集快照，固定顺序分段组装，校验与预算通过才更新本地单项缓存；只读模式实际移除run_main。入口practice.py --read-only；本地复用仍会发模型请求，不是API提示缓存。


第十一课[Error Recovery](s11-error-recovery/README.md)：只包装父模型请求，分类/退避/有界恢复，完整响应才交回原循环；已有工具结果保留，截断请求不执行。每轮4次、父会话20次尝试/3秒计划等待，源码与证据见docs/implementation/s11-error-recovery.md。


第十二课[Task System](s12-task-system/README.md)：单写者持久任务图，依赖检查/宿主认领/完成与解锁，跨进程恢复进度；任务状态不代替执行证据。公开入口init/show/work，设计与验证见docs/implementation/s12-task-system.md。


第十三课[Background Tasks](s13-background-tasks/README.md)：固定main.py显式后台启动，收据/进程结果/文本通知分别交接；轮次边界非阻塞检查，模型先停时由宿主回收并展示未消费结果，无忙等模型调用。


第十四课[Cron Scheduler](s14-cron-scheduler/README.md)：时间匹配、触发入队、空闲交付；固定UTC+08:00会话内表，执行权限独立，默认注入时钟，--serve-seconds才运行本进程调度线程。


第十五课[Agent Teams](s15-agent-teams/README.md)：独立成员上下文与追加式JSONL收件箱，reader接收reviewer信息后沿用原调查，queued和模型已读分开；12测试/18输入/SDK模拟HTTP。
