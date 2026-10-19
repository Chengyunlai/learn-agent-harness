# 第十课 System Prompt

Python3.10+标准库，先运行user_code，再读[core符号映射](core/README.md)。

```bash
python3 examples/s10-system-prompt/user_code/practice.py --decision allow
python3 examples/s10-system-prompt/user_code/practice.py --decision deny
python3 examples/s10-system-prompt/user_code/practice.py --read-only
python3 examples/s10-system-prompt/user_code/practice.py --read-only --no-skills
python3 examples/s10-system-prompt/user_code/verify_practice.py
python3 examples/s10-system-prompt/user_code/verify_fixtures.py
```

同一main.py/expected.txt检查。固定主/子模型；真实注册表、文件与获准进程。正常允许/拒绝各父5、子3请求，只读父4、子3；默认子只读工具不变。本地组装首次reused=False，后续为True，但每次仍调用模型。固定脚本直接按工具注册选择步骤，不证明真实模型理解system或因此更可靠。--live显式接真实主/子/必要时摘要模型，默认无在线模型或凭据。

collect_context读取宿主真实工作目录与注册，沿原工具定义生成器生成schema，去掉处理函数，只取技能/记忆元数据；没有用户消息关键词开关。assemble_system_prompt按identity/policy/tools/workspace固定顺序，加上实际存在的skills/memory目录；未注册run_main时明确未运行。权限仍由原执行入口决定，有工具不代表已批准。提示文本不是沙箱。

get_system_prompt将规范化上下文和实际TEMPLATES文本一起确定性JSON序列化。输入相同复用本地system与段落ID；工具描述/schema、工作目录、目录或模板变化都重新组装。错误/超过12000字节不更新旧缓存。上下文输入最多24000字节；不是API token窗口预算。返回深副本避免外部修改污染下一次读取。单进程、单项、串行教学缓存，不是API缓存，也不保证微小字符串拼接的性能收益；没有cache_control或线上缓存命中证据。

--read-only实际删除run_main；--no-skills实际删除load_skill并省略目录。没有热插拔或并发注册变更契约，运行期间工具集合由本次宿主配置固定。子任务仍沿前课独立system，本课重构父请求组装。原唯一run_loop、s08整理、s09记忆请求副本、计划/Hook/权限保持。

默认不加载项目记忆。需要验证可选memory段时，先执行第九课显式保存，再指定那个项目目录：

```bash
python3 examples/s09-memory/user_code/practice.py remember --approve
python3 examples/s10-system-prompt/user_code/practice.py --memory-dir examples/s09-memory/user_code/workspace/.memory --decision deny
```

system里只有目录；正文仍由s09附父请求副本，不自动提升到system。当前清单/历史/工具结果不进入本地system缓存键。目录用启动快照，修改文件要新运行；子不自动继承记忆。

验证21组标准库测试，含实际程序标记、只读强行请求未知工具仍拒绝、允许/拒绝不复用许可、模板/schema变化、失败保留旧缓存与完整输出反例；14同源教学绑定无API/进程，临时目录真实存在，工具注册仅供读取/校验，不执行其占位处理函数。缓存预热也用同源原函数。SDK1.13.0模拟HTTP允许/拒绝/只读分别8/8/7请求，核对system和tools字段、正文隔离及每次仍请求，无在线模型。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-system-prompt) · [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-system-prompt-practice)。
