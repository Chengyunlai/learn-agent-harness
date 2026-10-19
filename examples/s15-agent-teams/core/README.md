# 符号阅读

先运行 ../user_code/practice.py，按符号设断点：

- send_message：登记成员校验、绑定sender、读旧箱、容量、保存、queued收据。
- load_inbox/save_inbox：32001字节有界读取、完整字段/序号验证、同目录临时替换；单进程共享RLock。
- prepare_inbox：读取不删除、候选副本、完整通知去重、80条限制；交回原循环提交。
- run_teammate：锁内占用和2交付额度、历史副本、锁外run_turn、提交新历史/状态与finally释放。
- message_tool：sender由宿主闭包绑定，模型只提供recipient/body。
- user_code/practice.py run_member：自己的prefix+本轮历史，prepare只回当前后缀；原唯一run_loop/s10提示/s11父恢复/只读工具与Hook。
- demo：两个非daemon线程并行第一轮并join，再对reader追问，Lead单独接收报告。线程退出不等于成员上下文销毁。

邮箱消息ID（reader-1）与模型调用ID（reader-1-1）有各自作用域；工具收据queued不代表对方模型已经见到。
