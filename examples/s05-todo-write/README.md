# 第五课：TodoWrite

Python3.10+标准库。先读main.py和expected.txt，获准后真实运行，核对42。离线模型提交整份清单，状态保存在宿主内存，每次模型请求以副本附带当前计划；原循环不变。模型声明completed不会执行任务，也不证明完成。

```bash
python3 examples/s05-todo-write/user_code/practice.py --decision allow
python3 examples/s05-todo-write/user_code/practice.py --decision deny
python3 examples/s05-todo-write/user_code/practice.py --decision allow --maintenance
python3 examples/s05-todo-write/user_code/practice.py --decision allow --max-calls 4
python3 examples/s05-todo-write/user_code/verify_practice.py
python3 examples/s05-todo-write/user_code/verify_fixtures.py
```

正常8次模型调用后完成三项；拒绝/维护时第三项保留pending，仍可answered报告未执行。预算4会call_limit、保留未完成状态。默认ask只有交互终端确认，非TTY/EOF拒绝，--decision仅提供一次宿主固定回答。--live需显式配置ANTHROPIC_API_KEY/ANTHROPIC_MODEL，SDK固定anthropic1.13.0；默认与CI均不访问在线模型。

[core映射](core/README.md) / [实现记录](../../docs/implementation/s05-todo-write.md)。站点[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-todo-write) / [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-todo-write-practice)。

清单最多20项、唯一非空ID、三种状态、同时最多一项in_progress，空列表清空；整份替换，省略项会删除，失败保留旧列表。允许修正状态，未实现状态迁移审批/证据校验。执行工具仍经过s04 hooks和s03权限；todo_write有显式本地内存权限分支，禁止项与前置hook仍生效。s04 execute_hooked新增可选guard依赖，默认不变，不复制其执行前后控制流。

prepare_messages依赖原循环的首条user文本问题，复制后附加计划；不重写tool_result、不累积提醒、不修改历史。清单是用户数据，不作为system授权。无定时催更、Stop自动续跑、持久化/并发；任务标记与真实执行结果分开检查。

浏览器三函数11输入，纯内存真实执行，无模型/文件/进程替身需求；完整上下文可展开。verify_sdk模拟8次HTTP各允许/拒绝路径，工具数组schema/ID/当前计划/真实进程标记均检查。在线模型未运行。
