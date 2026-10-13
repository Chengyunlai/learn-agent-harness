# 第一课实现与发布记录

## 2026-10-13：独立 Python 实践仓库

用户要求小册读者能取得源码，将第一课实践移入独立公开仓库。新仓库从空目录初始化，只包含本课新编写的Python实现、测试、教学main.py、可选SDK依赖和必要文档，使用MIT许可；配套小册文章更新公开仓库链接。网站交互图和短代码轨迹回放在站点维护。

设计沿用一个具体问题：运行main.py，只报告结果。ask_claude调用一次模型；run_main执行固定文件；run_loop先保存完整assistant响应，再执行并保存关联tool_result，最后继续调用或返回明确状态。为了读者容易复现，默认scripted_model离线，文件真实执行；--live由读者显式选择。不新增权限、持久化、并发或目标完成判定模块。

运行入口为examples/s01-agent-loop/user_code/practice.py；映射为同课core/runtime.py，初始迁移实现保持原有符号和行为。阅读范围、实际验证和停止状态见根README。阶段实现、文档和CI在初始提交 `Publish Python Agent Loop practice` 一起发布，后续实践继续沿同仓库扩展。

实际验证：新目录公开入口输出真实除零结果，两次离线调用后answered；verify_practice.py的9项测试通过；独立SDK环境运行verify_sdk.py通过，HTTP全部模拟。迁移五个Python源文件逐一核对SHA-256与原实现一致；相对文档链接检查通过。默认入口和CI不访问在线模型。初始公开提交只包含审核过的教学文件，不继承站点Git历史。远程发布后再以匿名克隆及Actions结果复核。
