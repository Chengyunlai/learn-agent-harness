# 正式符号映射

先运行../user_code/practice.py init/show/work，再按符号读runtime.py。

| 符号 | 输入→输出 | 写入边界 |
| --- | --- | --- |
| create_task | ID/描述/已有依赖→新pending记录 | 校验整份候选后提交，不覆盖 |
| claim_task | ID/宿主负责人→in_progress记录 | 依赖全部完成后提交 |
| complete_task | ID/同负责人/结果说明→完成记录与新解锁ID | 先持久化完成，再求新可开始项 |

load_board/checked_board校验有界文件、状态与DAG；save_board单写者原子替换；ready_ids派生可开始项，不另外存blocks。build_task_tools绑定目录与owner，execute_task_call接回原Hook与分发；其余工具仍走既有权限。实践work复用s11父恢复、s10真实注册提示、s08整理与唯一run_loop，未复制循环。
