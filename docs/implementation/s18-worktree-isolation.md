# 第十八课设计与验证（2026-10-20）

问题：s17锁能管任务负责人，不能阻止两项任务同时覆盖同一路径。贯穿两个任务各改main.py，42与43并存，原目录0。创建、绑定工具路径、保留/清理三个完整函数；Git与task生命周期分开。会话内bindings，不改旧task/API。共享RLock短状态区；Git生命周期命令也串行锁内，10秒命令timeout，不作整体墙钟预算。工具/模型锁外，每成员一线程，active直到finally释放。

来源：2026-10-20核对https://learn.shareai.run/zh/s18/（学习方向），https://git-scm.com/docs/git-worktree（公共objects/refs、独立HEAD/index、add/remove），https://code.claude.com/docs/en/common-workflows（官方worktree使用说明）。不采信参考所谓Claude内部文件/行号，不声称本册教学API就是产品实现。

先执行s17公开入口，再编写s18与实际Git演示。14标准库测试、19原样函数教学输入通过；SDK1.13.0允许/拒绝各7模拟HTTP通过，恢复不重复写入。模型为固定替身，Git/线程/JSON/文件/获准进程真实；浏览器Git和看板读取明确内存替身。主目录0，两个目录42/43，脏目录保留；默认拒绝保留任务in_progress但干净目录可以移除，不等于任务完成。真实Git合并测试证实稍后仍会冲突。

限制：最多4绑定、任务ID32字符；会话内登记、不恢复成员；Git与内存登记无跨介质事务，超时/崩溃后先查worktree list；无force/删分支/自动合并/任意命令/沙箱/跨进程应用锁。主目录脏内容不复制，基于HEAD提交。默认临时演示进程末清理；--state-dir才保留供人工review。
