# 第十一课：Error Recovery

程序已经运行，准备报告结果时，模型请求返回429。恢复只重发这一轮模型请求；已执行工具及其完整交接继续保留。

Python3.10+，默认标准库，无API Key。从仓库根目录：

```bash
python3 examples/s11-error-recovery/user_code/practice.py --decision allow
python3 examples/s11-error-recovery/user_code/practice.py --decision allow --scenario truncated
python3 examples/s11-error-recovery/user_code/practice.py --decision allow --scenario fatal
python3 examples/s11-error-recovery/user_code/verify_practice.py
python3 examples/s11-error-recovery/user_code/verify_fixtures.py
```

默认固定父/子模型、固定故障注入；文件读取和获准后进程真实执行，等待仅记录不睡眠。允许路径父5次逻辑调用、6次请求尝试，子仍是前课独立3次固定判断；程序只执行一次。--decision deny明确拒绝，不通过恢复绕过许可。fatal/long_wait/truncated_twice/exhausted以model_error停止、CLI退出1，已有历史保留。exhausted在第一轮前连续529，没有工具执行。

三函数：[core映射](core/README.md)。classify_failure把规范化响应/失败分成accept/wait/expand/stop；retry_delay计算指数退避与有界比例抖动，优先有效Retry-After秒数；request_with_recovery仅包装一个模型请求。每轮最多4次尝试，父会话共享20次尝试、3秒**计划等待**额度；末次失败不再睡眠。1024→2048仅一次，再截断停下；候选响应不追加历史，不执行半截tool_use。输入和每次发送分别深复制。

400不凭错误文字猜上下文超限，413表示请求字节过大，两者都停下检查。第八课的完整交接整理仍在逻辑调用前运行；没有“只留最后几条”的反应式压缩。429也可能需要账户侧处理，重试额度耗尽仍会停止。没有续写拼接、模型切换、流式恢复、工具重跑或跨进程恢复。1024/2048为教学参数，实际模型必须支持相应限制；3秒不是整个任务的墙钟超时。父恢复不覆盖子模型与摘要，记录分别计量。

可选SDK验证使用requirements.txt固定Anthropic1.13.0及httpx2.MockTransport：

```bash
.venv/bin/python examples/s11-error-recovery/user_code/verify_sdk.py
```

HTTP全模拟，真实SDK序列化/异常适配，真实进程计数只增一次。sdk_send仅捕获类型化APIStatusError/连接/超时异常；不把普通Python异常归为可重试。SDK必须max_retries=0，防止双层放大尝试次数。

`--live`仅父请求访问真实API，要求ANTHROPIC_API_KEY与ANTHROPIC_MODEL；子模型/摘要仍为固定替身，网络超时20秒，正式等待使用time.sleep。公开验证未调用在线模型。工具进程按本机权限运行，是可信教学文件入口，未提供执行沙箱或进程树资源限制。

19组浏览器输入见user_code/figure_fixtures.py；三个函数原样执行。响应发送器为固定队列，等待器只收集秒数，随机源固定，均可展开查看。无API、工具执行或真实等待。配套[思想篇](https://www.chengyunlai.top/zh/blog/learn-claude-code-error-recovery)、[实践篇](https://www.chengyunlai.top/zh/blog/learn-claude-code-error-recovery-practice)。
