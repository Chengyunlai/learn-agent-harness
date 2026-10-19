# 正式源码映射

先运行../user_code/practice.py的remember与check，再按符号阅读runtime.py。

| 符号 | 职责 |
| --- | --- |
| validate_memory / validate_records | 严格字段、字符/数量上限、唯一名称 |
| load_memory / memory_catalog | 有界读取版本化单一JSON，派生无正文目录 |
| save_memory | 宿主明确确认后，临时写入与原子替换同名记录 |
| select_memories | 当前问题与元数据关键词匹配，稳定有界选择 |
| prepare_memory | 校验所有选择和附件预算，再附到深复制请求 |
| _s08.run_loop / prepare_context | 原唯一循环与请求前上下文整理，未另写循环 |
| user_code/practice.py: run | 启动项目快照、组装system、每次请求重新附带记忆 |

本课没有变更前课API。断点按save_memory的os.replace、select_memories的selected.append、prepare_memory的prepared[0]赋值符号定位；行号由固定源码摘录决定。
