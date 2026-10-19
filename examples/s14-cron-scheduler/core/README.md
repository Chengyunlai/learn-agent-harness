# 按符号阅读

先运行 ../user_code/practice.py，按符号设断点：

- cron_fields / cron_matches：注册前校验；UTC+08:00匹配分钟/小时/月，再处理日与星期。
- schedule_job / enqueue_due：有界会话表→UTC分钟ID→去重→队列容量→成功入队才记last_slot。
- dispatch_next：锁内busy/active/队列检查与占用，锁外run_turn，finally锁内结果+释放。
- cancel_job：删除未来表及未交付项，不取消active。
- build_schedule_tools：三个工具注册形状，默认定时轮次不开放新增调度权限。
- user_code/practice.py run_check：事件转新问题，原唯一run_loop、s10提示、s11恢复、旧工具许可/Hook。
- serve：独立生产线程与主线程消费者，stop/join生命周期；默认demo用同一个enqueue/dispatch和注入时钟。

cron-1是表ID；cron-1@UTC分钟是触发ID；step_1/step_2是单次模型轮次里的工具ID。三者作用域不同，不当作同一个任务或幂等键。
