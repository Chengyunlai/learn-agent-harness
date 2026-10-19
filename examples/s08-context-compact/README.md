# 第八课：Context Compact

Python3.10+，先运行，再读[core符号映射](core/README.md)。

```bash
python3 examples/s08-context-compact/user_code/practice.py --decision allow
python3 examples/s08-context-compact/user_code/practice.py --decision deny
python3 examples/s08-context-compact/user_code/practice.py --summary-limit 0
python3 examples/s08-context-compact/user_code/practice.py --budget 1600
python3 examples/s08-context-compact/user_code/verify_practice.py
python3 examples/s08-context-compact/user_code/verify_fixtures.py
```

贯穿问题：先读四份教学旧日志，再按output-check规范检查main.py与expected.txt，获准后运行并核对。旧日志刻意扩大历史；默认主/子/摘要均固定响应，不验证真实模型摘要质量。文件、压缩前JSONL快照与获准后的Python进程真实执行。默认父9次/子3次/摘要1次判断，父上限12、每次委派子上限4、整次父运行摘要最多尝试2次。SDK模拟HTTP覆盖这13次请求，在线模型未调用；--live须显式凭据与模型环境变量。

只在已收齐工具结果、下一次模型请求之前整理。split_history验证本例文本问题+完整工具请求/结果组，至少保留1组最近交接；不处理任意多模态、多轮用户续问或最终assistant答复。trim_results保留角色、调用ID、错误标记，只移出旧组中超过600字符的正文。prepare_context先写完整输入快照，再试廉价正文移出；仍超预算时摘要旧前缀并保留最近完整组。原问题由宿主持有，重建时明确带回；摘要只供参考，旧许可不授权新运行，旧技能需要重载。计划仍从宿主state附到每次请求副本，system目录与工具定义不由摘要修改。

预算3200是messages序列化JSON的UTF-8字节数，不是token数，也不包括system、工具定义和宿主计划附件；不能作为真实API上下文窗口上限。单条大结果、归档失败、摘要无效/截断、摘要预算耗尽或候选仍超限都停止，不无限重试。原run_loop的prepare在深副本上运行，成功才替换messages，失败返回context_error且不发本次模型请求；calls仅计父请求，不把摘要/子请求藏进这个计数。

快照保存在workspace/.context/，每次压力触发前保存一份输入，文件名唯一且不覆盖，单份最多1MB。多次压缩形成快照链；它不是每轮完整审计日志，也没有跨进程恢复协议。正文占位符写出收据及消息/块位置，便于宿主人手查JSONL；本课没有给模型注册归档检索工具。补读源文件不能自动重跑有副作用程序。归档失败不给收据，不丢内容；摘要失败可能已消耗尝试次数并留下快照，但不提交候选历史。

浏览器绑定原样执行三个函数和同源helper，在Worker临时虚拟文件真实归档；摘要使用公开固定文本替身。不访问宿主目录或真实模型。14输入、187行前帧；公开34断言验证协议、归档、候选提交、许可与完整输出反例。verify_sdk使用Anthropic1.13.0及httpx2.MockTransport，允许/拒绝各13请求及截断摘要拒收。普通Messages请求生成摘要，不是服务端Compaction API。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-context-compact) · [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-context-compact-practice)。
