# 实践 Examples

在仓库根目录运行，先 user_code，再 core。

| 课 | 问题与运行入口 | 核心实现 | 验证 |
| --- | --- | --- | --- |
| [第一课：Agent Loop](s01-agent-loop/README.md) | `python3 examples/s01-agent-loop/user_code/practice.py`：运行 main.py，只报告结果 | `core/runtime.py`：模型调用、固定工具、记录关联、有限循环 | `verify_practice.py` 真实进程；`figure_fixtures.py` / `verify_fixtures.py`三个原样函数八组教学输入；reading_demo保留；`verify_sdk.py` SDK模拟HTTP |

目前只有第一课。后续按实际实现追加，并更新本索引和阶段记录；不发布空目录。
