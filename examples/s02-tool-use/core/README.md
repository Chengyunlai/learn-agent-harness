# 实现映射

唯一正式实现为本目录runtime.py，先运行../user_code/practice.py。

- build_tools(workspace)：每项持有description、parameters和run闭包。
- tool_definitions(tools)：同一注册生成API说明，只支持本课必填字符串契约。
- execute_tool(call, tools)：调用ID由循环检查，这里检查名称、参数，再执行；输出/预期异常统一为关联tool_result。
- read_file(workspace,path)：解析路径→目录约束→有限读取→大小检查→UTF-8解码。
- _run_main(workspace)：适配第一课run_main，失败转为ValueError；不复制进程实现。
- ask_claude：一次SDK调用，传入生成的定义。
- run_loop：按文件路径加载第一课同一函数，保留消息/停止/顺序执行，只新增可配置问题参数。

断点按符号：execute_tool中的output调用前观察已通过校验；read_file中的target.open前观察目录检查通过；未知工具/错误参数/越界路径均不能到达相应执行行。figure_fixtures为可查看的边界替身，不修改这些函数正文。
