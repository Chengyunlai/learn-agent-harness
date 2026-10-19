# 符号阅读映射

先运行 ../user_code/practice.py。符号断点按以下顺序设置：

- start_background：校验、重复ID、许可/容量、launch、登记、收据。
- collect_background：snapshot为None即继续；完成记录固定并返回副本。
- prepare_background：从完成记录生成候选、以已提交文本去重、整份返回。
- ProcessHandle.snapshot/close：Popen.poll、直接进程超时kill/wait、输出读取和回收。
- user_code/practice.py 的 run：原run_loop prepare边界、新工具Hook装配、s11恢复和最终宿主回收。

没有第二份循环；没有线程触碰messages。模型停下后的未消费通知由CLI显示，不能称模型已看到。
