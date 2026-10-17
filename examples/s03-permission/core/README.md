# 权限实现映射

先运行../user_code/practice.py，再读本目录runtime.py。

- permission_for(call,tools,blocked)：validate_call检查契约；宿主禁止优先；read_file允许，run_main询问，无策略拒绝；不问、不执行。
- authorize_call(call,tools,ask_user,blocked)：allow/deny直接返回，ask才调用宿主；给宿主副本，只有bool True允许；宿主异常向上报告。
- execute_guarded(call,tools,ask_user,blocked)：先deepcopy请求，权限与执行使用同一快照；拒绝返回关联未执行结果，允许才调用第二课execute_tool。
- ask_claude：一次模型API；不决定宿主许可。
- 第二课build_tools/validate_call/execute_tool及第一课run_loop/进程按文件路径加载唯一实现。

断点按符号：authorize_call中的answer=ask_user处是等待宿主的位置；策略禁止到不了此行。execute_guarded最后return execute_tool是实际调用前，拒绝到不了此行。GUI只读摘录与公开figure_fixtures一致，不改正式body。终端确认入口terminal_approval在user_code中。
