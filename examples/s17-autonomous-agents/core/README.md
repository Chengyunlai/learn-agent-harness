# 正式符号映射

先运行../user_code/practice.py。

| 符号 | 读写职责 | 连续调用关系 |
| --- | --- | --- |
| runtime.scan_ready | 验证快照，筛pending/无owner/依赖全完成 | claim_next内部扫描 |
| runtime.claim_next | 锁内重读、再扫描、复用旧claim_task落盘 | idle_poll返回claimed后才工作 |
| runtime.idle_poll | 有界检查关闭和任务，锁外等待 | 每成员单工作线程调用 |
| runtime.shutdown_at_boundary | 核对真实请求/角色/正文，复用s16回复 | idle_poll优先调用 |
| user_code.practice.run_job | 自己历史+唯一原循环，按任务工具/权限 | run_teammate回调 |
| user_code.practice.finish_job | 核对真实工具结果后持锁完成 | 每轮工作返回后 |
| user_code.practice.demo | 创建3任务、2工作线程、收尾关闭、Lead一次汇总 | 公开CLI入口 |

看板沿用s12的20项/64000字节/原子替换；s17同进程所有写者必须共用RLock。s15成员2交付与独立历史、s16关闭协议、s10提示、s11恢复和原权限/Hook复用；不复制Agent循环，不修改旧API。断点按符号，不依赖行号。
