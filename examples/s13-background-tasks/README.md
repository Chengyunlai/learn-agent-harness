# 第十三课：Background Tasks

先运行公开入口，再读core。Python3.10+，默认标准库、固定模型、真实文件和直接子进程，没有在线模型开关。

```bash
python3 examples/s13-background-tasks/user_code/practice.py --decision allow
python3 examples/s13-background-tasks/user_code/practice.py --decision deny
python3 examples/s13-background-tasks/user_code/verify_practice.py
python3 examples/s13-background-tasks/user_code/verify_fixtures.py
.venv/bin/python examples/s13-background-tasks/user_code/verify_sdk.py
```

启动后立即保存一次tool_result收据；先读取expected.txt。main.py默认等待0.15秒，模型通常先回答“还在运行”；宿主不发模型轮询，等待有界进程并打印最终结果和未交给模型的通知数。测试用文件信号精确安排完成落在哪个轮次，而非依赖机器速度。

三个函数：[start_background → collect_background → prepare_background](core/README.md)。snapshot非阻塞；超时终止并wait直接子进程，关闭输出文件。回填候选失败或被丢弃时，结果仍在jobs；只有已提交历史中的相同通知才去重。输出作为普通user文本JSON通知，不给原tool_use_id追加第二个结果。

只启动固定main.py；最多登记4项（含已完成），保留至会话结束。重复调用ID返回旧收据，不启动第二次；新ID不是业务幂等键。许可仅布尔True，旧工具仍走原权限/Hook，新启动也走已有Hook包装及显式宿主许可。无命令字符串、关键词自动后台化或自动恢复。受信任示例无后代进程；仅管理直接子进程，不是沙箱/进程树资源控制，输出截取2000字节但临时文件没有磁盘配额。

第十二课任务图仍是持久工作记录，本课jobs仅会话内进程登记。没有改变任务completed，也没有保存运行句柄供新进程恢复。沿用唯一run_loop、s10真实提示注册与s11父请求恢复；短会话不叠加历史压缩/跨会话记忆，避免移走通知后又重新投递。模型结束仍会回收进程，但新结果只交给宿主，不暗中重开模型轮次。

浏览器figure_fixtures.py提供15输入，正式函数正文原样执行，TeachingHandle是可查看的进程快照替身，无真实进程或网络。SDK使用固定Anthropic1.13.0模拟HTTP，允许路径4次含一次529重发，拒绝路径2次，进程最多一次。
