# 正式源码符号映射

先运行../user_code/practice.py。

| 符号 | 职责 | 谁调用 |
| --- | --- | --- |
| runtime.open_request | 校验方向，邮箱保存后登记pending | submit_plan工具或宿主关闭入口 |
| runtime.reply_request | 绑定接收角色，保存决定，空闲确认关闭 | review_plan工具或宿主边界 |
| runtime.match_response | 关联ID/类型/信封角色及保存决定 | consume_responses |
| runtime.consume_responses | 统一扫描保留日志，重复匹配无副作用 | run_member.prepare及宿主 |
| runtime.plan_gate | 核对本次计划状态，不授予执行权限 | 旧execute_hooked.before |
| user_code.practice.run_member | 自己prefix+原循环后缀，原提示/恢复/权限 | 宿主阶段交付 |

旧s15文件邮箱与成员、s01唯一run_loop、s10提示、s11请求恢复继续复用。断点按符号，本课不修改旧API或循环。
