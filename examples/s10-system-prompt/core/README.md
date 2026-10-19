# 正式源码映射

先运行../user_code/practice.py，再按符号阅读runtime.py。

| 符号 | 职责 |
| --- | --- |
| checked_context | 严格字段/类型、确定顺序、无处理函数的JSON快照、有界输入 |
| collect_context | 工作目录与真实工具注册、技能/记忆目录生成 |
| assemble_system_prompt | 固定段落顺序、可选目录、缺少运行工具时如实说明 |
| get_system_prompt | 上下文+模板键、命中复用、完整组装及预算检查后提交 |
| TEMPLATES | 固定行为原则与目录边界，缓存键包含实际文本 |
| user_code/practice.py:run | 父请求组装，复用原循环/记忆副本/计划与许可 |

仅新增本课API，未修改旧课。分发仍使用同一实际注册，正式schema仍由原生成器放入SDK tools；提示中工具摘要不替代schema。断点按skill_catalog.append、sections.append、cache.update等符号定位。
