# 第十五课：Agent Teams

先运行公开入口，再读core。Python3.10+，默认标准库，固定模型、真实只读文件/线程/JSONL邮箱；没有在线模型或程序运行。

```bash
python3 examples/s15-agent-teams/user_code/practice.py
python3 examples/s15-agent-teams/user_code/practice.py --maildir /tmp/my-new-team-mail
python3 examples/s15-agent-teams/user_code/verify_practice.py
python3 examples/s15-agent-teams/user_code/verify_fixtures.py
.venv/bin/python examples/s15-agent-teams/user_code/verify_sdk.py
```

默认临时邮箱结束后清理；--maildir必须为空，可留下JSONL观察。reader读取main.py发lead，reviewer读取expected.txt发reader。第一轮真实并发，结束顺序不固定；两轮结束后向同一reader交付追问，它沿用原历史，不再读main.py，再发lead。Lead在自己模型轮次接入两条报告。正常9次逻辑请求，reader交付2次，lead/reader/reviewer邮箱2/1/0；只是只读信息，未执行程序。

三函数send_message/prepare_inbox/run_teammate，见[符号映射](core/README.md)。RLock保护单进程读改写与成员状态；JSONL按收件人追加序号，同目录临时文件原子替换，损坏不当作空、写失败保留旧记录。每收件箱8消息/正文600字符/文件32000字节，不删除已读消息。接入历史候选失败或丢弃仍可重读；以已提交的完整文本去重。读取不等于投递成功。

队友身份/上下文跨交付持续，执行线程只服务一轮；没有无限idle线程。本课固定lead/reader/reviewer，由宿主登记，不开放嵌套spawn。每队友最多2交付，每交付原run_loop最多4逻辑请求/父恢复最多20实际尝试。80条历史，answered后idle，其余停止/故障不自动继续；失败保留原上下文，但已发生文件/消息副作用不回滚。旧消息追加日志留盘不等于恢复历史或线程，重启入口拒绝非空目录。

前课run_loop/s10提示/s11恢复/工具注册与Hook复用；每次ask将自己prefix+本轮history提供给模型，prepare只接入下一边界新消息，不复制原循环。队友仅read_file/send_message，不注册run_main/bash/写文件。sender由宿主绑定，不是模型参数；这是本地角色约定，不是跨进程身份认证，消息不改变权限。文件共用同一进程RLock，无跨进程写锁或崩溃恰好一次保证。

18浏览器输入直接执行正式函数与同源存储helper/Worker虚拟文件/锁；run_turn为可查看的轮次替身。12标准库测试包括真实并发发信、真实两成员同时占用、拒绝同一成员重入、丢弃候选后接入、坏文件/原子替换失败/满箱、历史复用和停止。SDK1.13.0模拟HTTP10次（529一次），只保留三条消息，不重复发信。没有向真人或其他Codex会话发消息。
