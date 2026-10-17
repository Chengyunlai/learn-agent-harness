# 第三课 Permission（2026-10-18）

编辑卡：读者已理解循环和工具分发；新问题为参数合法仍需要宿主许可。单一案例先读main.py，运行前询问，print(6 * 7)。课程https://learn.shareai.run/zh/s03/核对2026-10-18，只取执行前权限的思路；官方权限文档https://code.claude.com/docs/en/permissions说明模型指令与强制权限分离。注册策略/同步回调/快照由本册独立实现，不复现Claude Code内部源码或课程命令黑名单。

设计：permission_for优先参数验证/宿主禁止，read_file allow、run_main ask、无策略deny；authorize_call仅ask调用宿主，显示副本，仅bool True允许；execute_guarded先copy请求，授权/执行同一snapshot，拒绝返回原ID的未执行结果。宿主异常向上传递不执行。CLI默认TTY y/N，非交互/EOF拒绝，Ctrl-C正常中断；--decision是一次教学回答，消费后拒绝，--block-run不询问。同步等待不调用模型，无持久化审批或恢复；不锁文件/不提供OS沙箱。

复用：第二课validate_call提取原检查，由分发/权限共用；fixture helpers同步。第一课循环/预算/消息/程序唯一实现不复制，日志文字改“处理工具请求”，避免提前宣称工具已运行。旧站点摘录保留固定历史版。

验证：9组标准库测试覆盖真实临时程序标记、允许、拒绝/禁止/参数错/宿主异常未启动、True严格判断、新工具默认拒绝、显示及原请求改动隔离、原ID和问题回传、重复拒绝预算。13组fixture原样执行3函数；宿主/文件/进程替身公开。SDK1.13.0/httpx2.MockTransport模拟允许/拒绝各3次请求，核对原ID、is_error与真实程序标记；在线模型未调用。第一课9项与第二课6项/fixture/SDK回归验证。CI加入第三课离线两路径/测试/fixture与SDK任务。

提交关系：父da59260419596f233cb9760c1b2075e02e68252c；本课实现、公开入口/验证、前课helper兼容调整、索引/context/本记录同次main普通提交。私有站点随后固定公开提交提取三个正文函数，配思想与实践两篇/各自内部SVG和同一断点游标。
