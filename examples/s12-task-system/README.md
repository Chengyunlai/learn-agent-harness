# 第十二课：Task System

Python3.10+，默认标准库。先运行user_code，再读[core符号](core/README.md)。任务文件单写者，不能同时开多个work进程。

```bash
python3 examples/s12-task-system/user_code/practice.py init
python3 examples/s12-task-system/user_code/practice.py show
python3 examples/s12-task-system/user_code/practice.py work --task check
python3 examples/s12-task-system/user_code/practice.py work --task run --decision allow
python3 examples/s12-task-system/user_code/practice.py work --task report
```

init只适用于新的任务目录；已有ID会拒绝，不重置。可用--store指定另一目录做独立实验。默认固定模型、真实JSON和文件/获准进程，不调用模型服务。三个work是三个新进程，恢复任务描述、依赖、负责人、状态和结果说明；不恢复旧对话或进程执行位置。依次解锁check/run/report，修订号最终9，程序仅执行一次。新进程报告明确引用先前run记录，不称为本次又运行。

create_task/claim_task/complete_task三正式函数分别创建、认领、完成；pending→in_progress→completed。创建只引用已有ID、不可改依赖或覆盖任务，因而新增边不会成环；加载仍检测缺失/自依赖/环。最多20项、文件64000字节、描述600字符、结果1200字符。单JSON先校验候选、临时写入flush/fsync后os.replace；单写者原子替换不等于并发认领事务或断电后目录保证。

五个注册工具task_create/list/get/claim/complete共用原分发；目录与负责人在宿主绑定，模型不能传owner或文件路径。task_create的dependencies是JSON数组**文本**，这是既有必填字符串工具契约的教学适配。任务记录工具在限定目录内更新，程序运行仍经过第三课许可。保留原唯一run_loop、Hooks/清单/Skills/子工具注册、s08整理、s10系统说明和s11父请求恢复；当前固定模型只使用当前机制所需工具，不能由此证明真实模型会正确规划。

--decision deny后run保留in_progress、report被阻塞；再次work不能重复认领或自动运行。真实输出不一致也不提交完成。中断时可能“进程已执行、完成尚未提交”，应先人工核对，再显式提交说明：

```bash
python3 examples/s12-task-system/user_code/practice.py complete --task run --owner worker-a --result "已核对已有执行记录，具体结果……"
```

结果说明由调用者提交，是持久记录，不能独立证明程序真实通过。没有自动解锁后执行、自动回退/抢占、锁、并行Agent、审计账本或恰好一次执行保证；负责人标识是宿主约定，不是多租户身份认证。本课无--live；SDK验证使用固定Anthropic1.13.0与httpx2.MockTransport，HTTP全部模拟。

```bash
python3 examples/s12-task-system/user_code/verify_practice.py
python3 examples/s12-task-system/user_code/verify_fixtures.py
.venv/bin/python examples/s12-task-system/user_code/verify_sdk.py
```

14组标准库测试含跨进程真实执行、阻塞、负责人、损坏/环、原子替换失败和输出不一致；15组浏览器绑定在Worker临时虚拟文件直接执行完整函数，故障替身仅替换失败接口。SDK验证允许+529/拒绝+阻塞两路，原父恢复不重复提交任务，不绕过运行许可；无在线模型调用。配套[思想篇](https://www.chengyunlai.top/zh/blog/learn-claude-code-task-system)、[实践篇](https://www.chengyunlai.top/zh/blog/learn-claude-code-task-system-practice)。
