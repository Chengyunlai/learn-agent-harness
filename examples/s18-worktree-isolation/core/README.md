# 正式符号映射

先运行../user_code/practice.py。断点按符号设置。

| 符号 | 职责与调用 |
| --- | --- |
| create_workspace | pending任务→Git工作树→内存绑定，不改任务状态 |
| workspace_for_task | 最新owner→Git归属/分支→active预留→工具路径 |
| retire_workspace | active门控→keep或检查dirty/HEAD→无force移除 |
| workspace_target / checked_workspace / git | 固定路径、实际Git归属、参数数组/10秒命令限制 |
| user_code.practice.demo | 真实临时Git、s17认领、s15交付、s01唯一循环，join后收尾 |
| user_code.practice.fixed_model | 固定写/运行/报告，SDK模拟HTTP也使用相同响应 |
| user_code.figure_fixtures | 原样函数，Git和看板读取公开内存替身 |

会话内bindings与s12持久任务分开；最多4目录，失败不伪造成功。cwd显式绑定，不切换全局目录。当前可信固定脚本示例不提供沙箱、跨进程恢复或自动合并。
