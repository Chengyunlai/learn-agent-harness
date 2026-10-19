# 第七课：Skills

Python3.10+，先运行，再读[core符号映射](core/README.md)。

```bash
python3 examples/s07-skills/user_code/practice.py --decision allow
python3 examples/s07-skills/user_code/practice.py --decision deny
python3 examples/s07-skills/user_code/practice.py --skill missing
python3 examples/s07-skills/user_code/practice.py --max-calls 1
python3 examples/s07-skills/user_code/verify_practice.py
python3 examples/s07-skills/user_code/verify_fixtures.py
```

目录常驻system，正文由load_skill工具反馈进入父messages。加载后会随历史继续发送，直到另行压缩/删除；本课不自动卸载、不缓存正文、不实现compact。只读子任务没有load_skill和技能目录，也不自动继承父已加载文本；委派须明确提供必要事实与要求。

默认固定模型替身证明请求装配，不证明真实模型会自动选对技能或遵守正文。真实读取SKILL.md、main.py与expected.txt，获准后真实运行Python。父5次、子3次离线判断；允许后按完整输出比较，拒绝后如实未执行。预算1只加载正文，父call_limit且不运行。默认ask仅交互终端询问，非交互拒绝；--allow/deny式固定回答为教学输入（实际参数为--decision）。

仅实现SKILL.md中name/description两个未加引号单行frontmatter字段，严格ASCII小写短横线名称且匹配目录，描述1到160字符；这是Agent Skills的教学子集，不是完整YAML或产品Skill执行器。头部最多32行/4096字节/每行512字节，目录最多20项。扫描只解码头部，不解析正文。加载按名称查注册表，重新resolve并检查宿主根目录，完整文件最多8192字节、UTF-8；过长拒绝，不截断规范。没有自动访问references或执行scripts。目录是启动快照，更新目录需重扫；已登记文件加载时读当前内容，未做版本锁定/并发防竞态沙箱。

load_skill为宿主显式允许的本地读取入口，仍经before/after Hook和参数校验。其他工具复用s06权限链，技能文字不能生成许可。只安装可信本地规范；能力/许可仍由Python控制，不在Markdown中解释执行。子任务读取工作目录的文件与技能目录加载是不同入口。

浏览器绑定使用tempfile创建该Worker内的虚拟临时文件，三个完整函数真实执行，不访问用户宿主文件系统，无模型/进程替身。公开verify_practice验证真实临时文件/进程；verify_sdk依Anthropic1.13.0+httpx2.MockTransport，允许/拒绝各8模拟HTTP，请求无在线模型。显式--live与ANTHROPIC_API_KEY/ANTHROPIC_MODEL才接真实API，本课未调用在线模型。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-skills) · [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-skills-practice)。
