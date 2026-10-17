# 第三课：Permission

问题：先读main.py；运行之前问我，得到允许后再运行并报告结果。

Python3.10+，根目录运行：

```bash
python3 examples/s03-permission/user_code/practice.py --decision deny
python3 examples/s03-permission/user_code/practice.py --decision allow
python3 examples/s03-permission/user_code/practice.py --decision allow --block-run
python3 examples/s03-permission/user_code/verify_practice.py
python3 examples/s03-permission/user_code/verify_fixtures.py
```

默认模型为固定响应，文件读取真实；只有获准才启动Python。decision是一次固定教学宿主回答，被消费后再问默认拒绝；不是模型参数或永久配置。默认ask在交互终端显示调用ID/名称/参数/理由，输入y才允许；非交互/EOF拒绝。同步等待期间不调用模型，无持久化审批或进程恢复。--block-run先按策略禁止，不询问用户；--max-calls1只读后停。--live按根README配置SDK和凭据才请求在线模型。

先运行user_code，再读[core映射](core/README.md)。权限函数permission_for→authorize_call→execute_guarded；第二课validate_call/execute_tool与原循环/进程复用。请求快照确保确认与执行参数对应，不锁定文件，不提供OS沙箱。

已验证9组测试：真实程序标记证明允许才启动；禁止/拒绝/参数错/宿主异常未执行，bool True规则、无策略默认拒绝、显示与原请求修改隔离、ID/原目标回传、预算。13组浏览器绑定：函数原文执行，宿主/文件/进程是公开替身。可选SDK1.13.0的verify_sdk.py用模拟HTTP对照允许/拒绝，各3次请求，真实标记结果一致；没有在线模型验证。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-permission) / [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-permission-practice)。
