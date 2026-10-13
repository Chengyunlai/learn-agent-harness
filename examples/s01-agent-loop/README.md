# 第一课：Agent Loop

问题：“运行 main.py，只报告结果。”默认 main.py 的 `10 / 0` 使程序失败，Harness 把真实错误保存并回传；模型回复结束与程序成功分别判断。

从仓库根目录运行：

```bash
python3 examples/s01-agent-loop/user_code/practice.py
python3 examples/s01-agent-loop/user_code/verify_practice.py
```

默认入口明确标注离线模型替身；main.py真实执行。两次调用后状态answered，报告除零错误。`--max-calls 1`取得并保存结果后以call_limit停止，退出码1。`--workspace`指定本地教学目录。在线模式和SDK验证的依赖安装见[根README](../../README.md)。

运行后读 [core映射](core/README.md)，再读 runtime.py。文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-agent-loop) / [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-agent-loop-practice)。


站内断点实验对应 `user_code/reading_demo.py`，可独立运行，无SDK/进程依赖。默认max_calls4、truncatedFalse；改成max_calls1观察保存后停下，truncatedTrue观察执行前停下。`python3 examples/s01-agent-loop/user_code/verify_reading.py`验证三个变体。短代码省略正式运行时的参数/协议检查、网络与文件进程，不能替代完整实践入口。
