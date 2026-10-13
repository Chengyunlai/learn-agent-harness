# 第一课实现与发布记录

## 2026-10-13：独立 Python 实践仓库

用户要求小册读者能取得源码，将第一课实践移入独立公开仓库。新仓库从空目录初始化，只包含本课新编写的Python实现、测试、教学main.py、可选SDK依赖和必要文档，使用MIT许可；配套小册文章更新公开仓库链接。网站交互图和短代码轨迹回放在站点维护。

设计沿用一个具体问题：运行main.py，只报告结果。ask_claude调用一次模型；run_main执行固定文件；run_loop先保存完整assistant响应，再执行并保存关联tool_result，最后继续调用或返回明确状态。为了读者容易复现，默认scripted_model离线，文件真实执行；--live由读者显式选择。不新增权限、持久化、并发或目标完成判定模块。

运行入口为examples/s01-agent-loop/user_code/practice.py；映射为同课core/runtime.py，初始迁移实现保持原有符号和行为。阅读范围、实际验证和停止状态见根README。阶段实现、文档和CI在初始提交 `Publish Python Agent Loop practice` 一起发布，后续实践继续沿同仓库扩展。

实际验证：新目录公开入口输出真实除零结果，两次离线调用后answered；verify_practice.py的9项测试通过；独立SDK环境运行verify_sdk.py通过，HTTP全部模拟。迁移五个Python源文件逐一核对SHA-256与原实现一致；相对文档链接检查通过。默认入口和CI不访问在线模型。初始公开提交只包含审核过的教学文件，不继承站点Git历史。远程发布后再以匿名克隆及Actions结果复核。


发布复核：公开仓库visibility=PUBLIC、默认分支main；初始提交8f33e64e9e5bf487e1d04006ac7a74e2c7a60d4b。关闭Git credential helper和额外HTTP认证头后，匿名HTTPS下载成功；在下载的临时目录运行入口、9项标准库测试与SDK模拟HTTP验证，全部通过。GitHub Actions [38356056415](https://github.com/Chengyunlai/learn-agent-harness/actions/runs/38356056415)成功：Python3.10/3.13的离线入口/测试、Python3.13的SDK报文验证均通过。在线模型未调用。此发布证据随独立后续记录提交保存，不修改初始源码版本。


## 2026-10-13：实践文章的分步阅读与教学断点

用户要求不打开源码也能理解实现，文章按准备记录、首次调用、保存请求、执行程序、取得结果、保存并查预算、再次调用、正常返回八个时刻呈现。调用上限在第六步交回控制权；截断在第三步停止而不执行。图为实现推演，不作真实模型日志。

新增公开reading_demo.py，消息/工具块及调用ID采用相同协议形状；模型固定响应、文件进程替换为直接10/0，异常真实捕获。浏览器重用此短代码，切换输入max_calls/truncated验证三分支。短代码省略正式程序其他校验与网络/进程处理，完整runtime保持原样。

实际验证：公开短代码独立运行输出保存call_1和answered；verify_reading.py以CPython行前快照验证请求先保存才执行、工具反馈保存前后2/3条记录、错误ID对应、正常2次调用4条终态记录、上限1次调用3条记录、截断1次调用2条记录且没有执行函数。均通过。站点正式采集器也执行三变体，事件数量34/26/15，保存前的result与少量变量可见。阶段代码、导航和CI修改同次提交 `Add browser teaching loop and trace verification`，父提交07d7f4b375e334d0f42de807f006dd8133138195。完整SDK和真实进程入口保持独立，在线模型未调用。

## 2026-10-13：原样函数的浏览器教学绑定

用户要求代码块的debug单步直接带动SVG，并形成可复用方案，替代图与独立短代码各自推进。新增figure_fixtures.py/fixture_context：八组输入包括模型请求1组、工具成功/失败/超时/拒绝4组、循环正常/上限/截断3组。setup准备SDK/进程替身，entry调用原样正式函数，watch/scopes为站点真实采集器提供观察范围。loop需要的两个adapter从core函数inspect.getsource提取，未另写或改造循环。API和进程边界被替代，函数本身实际执行，全部明确标注。站点将上下文生成展示绑定并复用原PythonDemo控制轨迹。

实际验证：verify_fixtures.py执行core三个原样函数，八组输入的ID、错误标记、工具次数、两次/一次调用、4/3/2条记录和不执行路径全部通过；原9项进程测试、reading_demo验证与SDK模拟HTTP验证保留。站点正式trace_code对同组输入产生6/16/16/11/4/50/37/20事件，准备脚本/调用入口不进入源码行号，写回前后2/3条记录得到真实快照验证；普通运行与调试输出一致。没有访问在线模型，浏览器替身没有启动进程。公开Python源码runtime.py与旧版本一致。

同步根README、context、examples/core导航与3.10/3.13 CI；父提交abfe22c77f2dd85219c77d591af9accfe21c7ee0，本轮提交 `Add explicit teaching bindings for source-driven figure debugging` 普通推送main。站点通用PythonFigure及collector改动独立提交，相关版本以发布结果核对。
