# 正式符号

唯一实现runtime.py：run_hooks（顺序、阻止与观察故障）、execute_hooked（包住s03权限）、audit_event（提取审计字段）。build_tools/run_loop/ask_claude通过s03复用，底层仍为s02工具/s01循环。user_code/practice.py的build_hooks负责注册，并将report.result交给原循环；warnings留在宿主，未塞入工具协议。fixture按inspect读取原函数，不维护另一套实现。
