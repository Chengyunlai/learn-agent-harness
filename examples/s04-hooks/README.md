# 第四课：Hooks

问题：读取/运行工具前增加维护检查，处理后增加审计，是否需要继续修改循环？

Python 3.10+；默认离线模型替身，真实文件与进程，审计保存在内存。运行前仍由第三课权限入口询问；非交互环境默认拒绝。`--decision allow/deny` 仅提供一次固定宿主回答。

```bash
python3 examples/s04-hooks/user_code/practice.py --decision allow
python3 examples/s04-hooks/user_code/practice.py --decision allow --maintenance
python3 examples/s04-hooks/user_code/practice.py --decision allow --audit-failure
python3 examples/s04-hooks/user_code/verify_practice.py
python3 examples/s04-hooks/user_code/verify_fixtures.py
```

正常输出42；维护时返回“未执行”，不询问运行许可；后置审计失败时仍输出42，另有宿主警告。前置日志先登记请求，后置日志登记处理结果，拒绝也登记。`after`在本章指入口取得结果之后，包含拒绝/工具错误；不是Claude Code仅成功事件PostToolUse的同义名。权限接口意外异常仍向上传播，不触发after，不伪造结果。

先运行user_code，再看[core映射](core/README.md)。[阶段设计与验证](../../docs/implementation/s04-hooks.md)。配套[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-hooks) / [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-hooks-practice)。

`run_hooks`按注册顺序同步执行，一次触发使用注册表快照；每个回调收到payload深拷贝。before返回None继续，非空字符串阻止，异常或错误类型也阻止。after必须返回None，异常/错误返回只产生警告，后续观察者继续。`execute_hooked`仍调用第三课execute_guarded，hook不能以allow覆盖宿主权限。宿主装配代码可信；拷贝不能把恶意回调变为沙箱代码。

浏览器教学原样执行三个函数正文，宿主、文件和进程由figure_fixtures公开替身提供，12种输入。标准库测试使用真实程序标记证明执行次数。`verify_sdk.py`使用固定anthropic1.13.0和httpx2.MockTransport模拟HTTP，保留实际文件/进程；不访问在线模型。`--live`沿用显式环境变量入口。

当前没有Stop hooks、自动续跑、异步并发、持久化审计或第三方脚本加载。预算和停止条件继续使用第一课循环。回调必须短且可信；同步回调阻塞会阻塞宿主，捕获Exception不能处理卡死。
