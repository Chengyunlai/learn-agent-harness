# 第十七课：Autonomous Agents

Python3.10+，默认标准库。先运行user_code，再沿core符号阅读。固定模型；真实双线程、JSON任务看板/JSONL邮箱与获准后的Python进程；没有在线模型。

```bash
python3 examples/s17-autonomous-agents/user_code/practice.py --decision allow
python3 examples/s17-autonomous-agents/user_code/practice.py
python3 examples/s17-autonomous-agents/user_code/verify_practice.py
python3 examples/s17-autonomous-agents/user_code/verify_fixtures.py
.venv/bin/python examples/s17-autonomous-agents/user_code/verify_sdk.py
```

宿主创建source/expected/verify三项固定任务，verify依赖前两项。reader/reviewer都是能处理固定任务的成员，各有一个工作线程；自主选择由宿主idle_poll发现/认领，不让Lead逐项assign，也不让模型在空闲时持续调用。谁认领哪项由并发时序决定，不能把一次终端顺序当成协议。允许时三项completed，程序输出42与读取的预期一致；默认拒绝运行，verify保留in_progress/owner，先前两项仍completed；预期改成43也不能误完成。每任务唯一实际read或run请求+回答，Lead单次汇总，共7逻辑请求。

三个函数：[scan_ready / claim_next / idle_poll](core/README.md)。scan_ready只看快照；claim_next在全队同一RLock内重读/扫描/认领，复用s12保存后才返回claimed；所有任务写入均使用这把锁。单进程多线程安全，无跨进程文件锁；默认状态目录临时清理，--state-dir必须为空，不自动恢复历史、抢占或重试进行中任务。任务文件保留进度不等于恢复成员。

idle_poll先检查自己的可交付状态，再处理实际关闭协议，之后才认领。等待放锁外，用Event.wait(.05)；默认最多3次检查/2次等待，checks允许1..12，idle_timeout只是这些检查没找到工作，不证明看板全部完成。普通消息保留到下次实际工作prepare，不单独唤起空模型。工作阶段不抢断，关闭在本线程下一空闲边界处理；最终宿主join后再请求关闭。关闭确认保存后成员closed，Lead再匹配approved，复用s16原协议。每成员仍2次交付，每轮原run_loop最多4逻辑请求/请求恢复20实际尝试；失败留任务in_progress，不自动重跑有副作用的工具。

默认工作阶段没有模型提新计划，只执行宿主登记的三种固定任务，不自动批准计划。工具按任务选择read_file或run_main，前置校验当前任务负责人和固定路径，原权限/Hook仍有效；--decision与自动认领独立。finish_job读取当前轮真实tool_result而非模型完成宣称，核对输出后才complete_task。完成说明本身不是一般性的正确性证明。

13标准库测试包括真实并发唯一认领、两个读取任务并行、旧快照重检、依赖解锁、保存失败保留、等待不持锁/新任务和关闭到达、关闭优先、空闲不调用模型、错误路径不完成。22同源浏览器输入用Worker虚拟文件和真实锁，等待回调公开注入新任务/中断，无实际睡眠/线程/程序。SDK1.13.0三路径各8模拟HTTP含529，任务3项无重复，Lead邮箱5条，允许路径程序计数x；不承诺一般崩溃恢复后的恰好一次。
