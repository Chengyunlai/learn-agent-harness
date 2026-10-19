---
name: output-check
description: 核对Python程序输出与expected.txt，区分推导、运行和未执行。
---
# 输出核对流程

先委派只读检查main.py与expected.txt；源码推导不能写成运行结果。
父流程重新读取expected.txt，运行前取得宿主许可。
允许后检查退出码，再比较完整输出正文与预期，不只比较最后一行。
最后按“是否执行 / 退出码 / 核对结论”报告；拒绝时明确未执行。
