# 第二课：Tool Use

问题：先读 main.py，再运行它，报告文件内容和运行结果。

Python3.10+，根目录运行：

```bash
python3 examples/s02-tool-use/user_code/practice.py
python3 examples/s02-tool-use/user_code/verify_practice.py
python3 examples/s02-tool-use/user_code/verify_fixtures.py
```

默认模型为固定响应，真实读取 `print(6 * 7)` 并运行得到42；3次判断后answered。`--max-calls 1`只保存读取结果，以call_limit退出1。可选`--workspace`指定可信教学目录；`--live`需要按根README配置SDK和凭据，才会请求在线模型。

先运行user_code，再读[core映射](core/README.md)。`build_tools`注册read_file与run_main；`tool_definitions`生成模型说明；`execute_tool`校验与调用；`read_file`检查解析路径、最多读取4097字节并拒绝超过4096字节文件，再UTF-8解码。程序执行与循环复用第一课源码；第一课run_loop新增可选question，默认保持原行为。

浏览器 `figure_fixtures.py` 提供3函数8组教学输入；函数原文执行，虚拟路径/字节文件和进程是替身，准备与入口可在文章展开查看。它不代替真实文件测试。SDK验证使用anthropic1.13.0 + httpx2.MockTransport：

```bash
.venv/bin/python examples/s02-tool-use/user_code/verify_sdk.py
```

已验证：真实读/运行、6组标准库测试、8组教学输入、3次模拟HTTP。在线模型尚未验证。路径检查不消除文件系统竞态，运行工具仍具有本机权限；仅使用可信教学文件。

文章：[思想](https://www.chengyunlai.top/zh/blog/learn-claude-code-tool-use) / [实践](https://www.chengyunlai.top/zh/blog/learn-claude-code-tool-use-practice)。
