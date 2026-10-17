# 实践 Examples

在仓库根目录运行，先 user_code，再 core。

| 课 | 问题与运行入口 | 核心实现 | 验证 |
| --- | --- | --- | --- |
| [第一课：Agent Loop](s01-agent-loop/README.md) | `python3 examples/s01-agent-loop/user_code/practice.py`：运行 main.py，只报告结果 | `core/runtime.py`：模型调用、固定工具、记录关联、有限循环 | `verify_practice.py` 真实进程；`figure_fixtures.py` / `verify_fixtures.py`三个原样函数八组教学输入；reading_demo保留；`verify_sdk.py` SDK模拟HTTP |
| [第二课：Tool Use](s02-tool-use/README.md) | `python3 examples/s02-tool-use/user_code/practice.py`：先读文件，再运行 | 注册/分发/有限读取；复用第一课循环 | verify_practice、verify_fixtures、verify_sdk |

| [第三课：Permission](s03-permission/README.md) | `python3 examples/s03-permission/user_code/practice.py --decision deny` / `--decision allow` | 策略/宿主确认/执行快照；复用第二课和循环 | 9组真实执行测试、13输入、SDK模拟HTTP |

第二课新增两项工具的注册、分发与路径读取，复用第一课循环。后续按实际实现追加，不发布空目录。
