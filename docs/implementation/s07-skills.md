# 第七课Skills（2026-10-19）

编辑卡：已读前六课的Python读者；问题是无关规范挤占上下文。沿main.py/expected.txt/运行许可，增加output-check与不相关sql-style。输入是技能名，输出是完整有界正文，之后仍需读文件/许可/执行；加载不自动变更工具能力。主线：头部注册→名称/描述目录→按需正文→当前历史保留→执行证据。参考课程https://learn.shareai.run/zh/s07/、官方https://code.claude.com/docs/en/skills、Agent Skills https://agentskills.io/specification，核于2026-10-19；不采用课程不明来源内部源码分析。

本实现仅两字段单行frontmatter教学子集、目录最多20、文件8192字节；scan只解析有界头部，load不接受任意路径/脚本执行，未实现缓存/卸载/自动选取。父工具保留清单/子任务/Hook/权限，子上下文不继承skill目录或正文。文件更新不锁版本，resolve边界不声称防并发竞态或OS沙箱。

实际verify_practice 25断言：目录无正文、重复组装、正文延迟解码、名称与符号链接边界、大小/编码错误、恶意正文不能越过许可、原ID/子不继承、预算、Hook阻止、完整输出反例。11虚拟文件绑定通过正式trace_code共129帧；同源函数与helper真实执行。SDK1.13.0允许/拒绝各8模拟HTTP验证目录在system、正文首次load后进入父messages并保留、无SQL正文、子只读定义。在线模型未调用。

此提交作为站点按符号与固定hash提取的公开源版本。CI保留前课，增加s07离线/绑定/SDK；站点提交另记文章、图和页面验证。
