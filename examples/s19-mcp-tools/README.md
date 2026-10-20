# 第十九课：MCP Tools

Python3.10+。桥接核心/教学绑定只需标准库；真实stdio需本课可选mcp==1.26.0，模型HTTP契约还需根anthropic==1.13.0。先运行user_code，再按core符号阅读。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r examples/s19-mcp-tools/requirements.txt
.venv/bin/python examples/s19-mcp-tools/user_code/practice.py --decision allow
.venv/bin/python examples/s19-mcp-tools/user_code/practice.py
.venv/bin/python examples/s19-mcp-tools/user_code/practice.py --decision allow --mode tool_error
python3 examples/s19-mcp-tools/user_code/verify_practice.py
python3 examples/s19-mcp-tools/user_code/verify_fixtures.py
.venv/bin/python examples/s19-mcp-tools/user_code/verify_mcp.py
# 安装根requirements后可运行本课verify_sdk.py
```

固定模型；官方MCP SDK ClientSession与本仓库拥有的低层Server通过真实stdio子进程通信，协商2025-11-25，实际tools/list、tools/call；读取本地policy.txt。没有在线模型、外部业务服务、网络MCP或真实用户程序执行。宿主只启动已知本课server.py，不接受模型提供可执行命令。初始化/能力核对完成后才进入旧唯一run_loop；load_docs_tools只发现并接入已连接服务的目录，不假称这个工具创建了进程。

三个核心函数discover_tools/assemble_tool_pool/call_external。完整发现后才返回目录；最多4页/8工具/单页24000字节，重复名称/游标或超限失败。只支持显式type/properties/required/additionalProperties=false且最多4个必填字符串字段的schema，字段32字符、实参每项120字符；不支持的schema整次拒绝，不静默改写成空参数。服务ID小写字母数字短横线16字符、最多2服务，工具ASCII字母数字点短横线下划线32字符。点映射为下划线后检查冲突，与内置重名也拒绝，旧池保持。外显mcp__docs__search_docs通过路由回原search.docs；定义与路由同一快照，不反向拆字符串或靠循环闭包猜provider。

外部调用前宿主独立确认，readOnlyHint不自动授权；默认拒绝。参数与确认副本分开，工具反馈关联原模型tool_use_id（MCP自身JSON-RPC ID由SDK管理）。支持1..4块非空纯文本、合并后2000字符、isError布尔；结构化/多媒体等本课不接收，明确报错，不悄悄丢字段。业务isError原样映射；传输/超时可能发生在服务已接受调用后，无自动工具重发。SDK请求读取5秒，桥接等待6秒，初始化与stdio上下文由同一事件循环创建/关闭；同步原循环用asyncio.to_thread，run_coroutine_threadsafe投回原loop，禁止在该loop线程直接等待同步bridge。

正常路径4逻辑模型请求：发现目录→查询服务→读本地文件→回答。默认拒绝/业务错误3次；坏schema2次，旧工具池不变。system、请求definitions与执行route从当前快照派生，沿用s10基于实际能力的缓存键，新增工具后reused=False，后续相同配置复用；不必删掉整个缓存。会话只单线程更新工具池，不处理list_changed、断线重连、热撤销、OAuth、远程HTTP、资源/提示等机制，不把标准化接入当成任意工具无适配。

11标准库测试/21同源教学输入；真实MCP四路径与一次已接受请求超时不重发；Anthropic1.13.0模拟HTTP允许5/拒绝4次（含工具反馈后529），真实MCP调用1/0次，不重复外部执行。浏览器原样函数+公开分页/调用内存替身，不启动MCP或访问本机文件。
