# 第九课 Memory

Python3.10+，标准库运行。先运行user_code，再读[core符号映射](core/README.md)。

```bash
python3 examples/s09-memory/user_code/practice.py remember --approve
python3 examples/s09-memory/user_code/practice.py check --decision allow
python3 examples/s09-memory/user_code/practice.py check --decision deny
python3 examples/s09-memory/user_code/practice.py check --decision allow --question '检查并核对，本次用一句话报告，运行前问我。'
python3 examples/s09-memory/user_code/verify_practice.py
python3 examples/s09-memory/user_code/verify_fixtures.py
```

第一条命令是宿主确认保存稳定偏好；没有--approve会拒绝写入。候选完整内容在user_code/report-memory.json，默认写到workspace/.memory/memory.json。后面的check命令每次都是全新会话、新计划与许可；原历史不跨进程恢复，只有项目记忆文件留下。--memory-dir由宿主选择项目范围，另一个目录不继承。可用--candidate指定人工审核的JSON，更正同name记录；删除memory.json可忘记本例全部记忆，不重建旧会话。

save_memory校验候选后写同目录临时文件、flush/fsync、os.replace；一个JSON既保存正文也保存元数据，启动时生成目录，无第二份索引需同步。最多20条、单文件64000 UTF-8字节、正文1200字符。单写者教学实现，无并发更新锁；原子替换避免旧文件半写，不承诺断电持久性。损坏文件报错，不当空库覆盖。目录由可信宿主配置，非任意代码沙箱。

select_memories只按明确keywords在当前问题中不区分大小写匹配，按name顺序最多2条（允许1–3）；不是语义检索。目录不含正文或来源全文。小JSON在宿主启动时整份读取，只有选中正文进模型请求；不声称磁盘上只读了元数据。prepare_memory先核对全部名称与附件4096字节预算，深复制消息后附带。未知项/超预算拒绝，不提交半份附件，不截断。当前问题/工具ID/is_error不被替换；每次从活跃历史生成副本，不累积附件。

装配保留原s01唯一循环、s08请求前整理、s07技能、s06子任务、s05计划、s04Hook与s03许可。system增加元数据目录，父请求副本附选中正文；压缩后仍从宿主持有的启动快照附带，子任务不自动继承。本次新会话内不热重载，改文件要在下次check加载。写入只在显式remember入口，不从模型响应/摘要自动提取，也不注册模型记忆写工具。没有LLM选择/提取、向量库、自动合并或恢复旧运行。

默认主/子模型都是固定响应；文件、记忆保存、新进程加载与获准程序真实执行。报告格式变化由教学脚本固定分支演示，不能证明真实模型一定遵循记忆或自然理解冲突。20测试覆盖跨进程读取、拒绝/错误替换不改旧文件、当前要求优先、恶意旧许可不能启动进程、完整输出多一行不能判一致。14浏览器输入真实执行原样三个函数与同源helper，文件在Worker临时虚拟目录；replace_error仅注入可见故障接口，不访问宿主文件。SDK1.13.0允许/拒绝各8模拟HTTP请求（父5/子3），无在线调用。--live显式接主/子/必要时摘要模型，单独计费；默认没有记忆模型请求。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-memory) · [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-memory-practice)。
