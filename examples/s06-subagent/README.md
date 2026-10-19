# 第六课：Subagent

先运行公开入口，再读[core符号映射](core/README.md)。Python3.10+，离线入口只用标准库。

```bash
python3 examples/s06-subagent/user_code/practice.py --decision deny
python3 examples/s06-subagent/user_code/practice.py --decision allow
python3 examples/s06-subagent/user_code/practice.py --decision allow --child-calls 1
python3 examples/s06-subagent/user_code/verify_practice.py
python3 examples/s06-subagent/user_code/verify_fixtures.py
```

贯穿问题：委派助手读取main.py与expected.txt，得到源码推导；父流程重新读取预期文件，获准后运行并核对。子任务只得到委派文本，不获得父历史；只注册read_file，不能运行、写计划或递归委派。同步等待，子循环默认最多4次模型请求（可设1到8），父循环默认4次。预算限制请求数，不限制单响应工具数或总token；没有并行调度、取消、跨进程隔离或恢复。

默认固定模型替身只分析`print(6 * 7)`这一教学样本，文件与获准后的进程真实执行。允许路径父4次、子3次模型判断，输出42并核对；拒绝路径报告未执行。子预算1会读完一个文件后停为call_limit，父流程收到is_error，不发起运行。answered只说明有回答，不能担保结论正确。

第五课清单仍可用，按请求副本附加；默认脚本聚焦子任务，不重复四次清单更新。父task和子read均经过Hook/权限入口；子Hook是独立的本地审计回调，不自动继承父宿主自定义策略。实际项目应显式传递必要策略，不能把本例当作完整授权继承方案。文件读取仍受第二课目录与字节限制。上下文隔离不等于文件系统沙箱；若未来给子任务写工具，副作用会落在相同工作目录。

`figure_fixtures.py`公开浏览器绑定：完整函数正文执行，但run_subagent中的原循环、模型和文件入口为简短内存替身，便于逐行观察边界；真实嵌套循环由verify_practice验证。child_tools/task_result纯内存，无外部调用。站点图复用PythonFigure唯一断点，不另设阶段游标。

可选安装requirements.txt后运行verify_sdk.py；固定Anthropic1.13.0和httpx2.MockTransport，允许/拒绝各7次模拟HTTP，检查父子system/tools/历史及关联ID。`--live`需显式ANTHROPIC_API_KEY与ANTHROPIC_MODEL，访问真实模型；本课交付未调用在线模型。

配套：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-subagent) · [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-subagent-practice)。
