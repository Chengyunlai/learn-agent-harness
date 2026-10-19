# 正式符号映射

先运行../user_code/practice.py，再按符号阅读runtime.py。

| 符号 | 输入与输出 | 不承担的职责 |
| --- | --- | --- |
| classify_failure | SDK适配后的基本数据→恢复动作及原因 | 不解析任意错误文本、不批准工具 |
| retry_delay | 尝试序号/秒数头/抖动比例→计划秒数 | 不睡眠、不偷偷缩短服务器要求 |
| request_with_recovery | 发送器/请求/父会话额度→完整响应或RecoveryStopped | 不写历史、不运行工具 |

sdk_send把固定SDK类型化异常转成基本数据；checked_state检查宿主状态。s10公开run装配仍负责system、计划/记忆、权限与s08整理，s01唯一run_loop仍负责保存与分发。s10入口的模块导入改为按路径绑定自身core，公开函数签名/行为不变，避免s11的同名runtime冲突。父会话剩余额度由调用者持有，子调用独立。
