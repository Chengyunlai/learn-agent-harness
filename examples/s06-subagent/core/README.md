# 符号映射

先运行../user_code/practice.py。正式实现只在runtime.py：

- child_tools(tools)：从宿主注册表复制read_file白名单；缺失时失败。
- run_subagent(task,tools,ask,max_calls,emit)：验证委派与预算，独立工具表，复用s01.run_loop创建新消息，返回子outcome供宿主记录。
- task_result(call,outcome)：只把status/summary/calls写入原ID的tool_result；失败和过长结论标is_error。
- build_tools：扩展s05清单工具和task闭包，宿主可保留traces。
- execute_with_subagent：task本地分派，todo_write更新内存，其他工具仍走s03权限；统一经过s04前后Hook。
- ask_claude：一次SDK请求，父/子system及工具定义分开；子工具用s02字符串schema。

符号断点：child_tools、run_subagent、task_result，不固定行号。user_code/figure_fixtures.py按相同符号提供教学输入及明确替身。
