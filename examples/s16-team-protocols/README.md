# 第十六课：Team Protocols

Python3.10+，默认标准库。先运行user_code，再按core符号阅读；固定模型、真实JSONL邮箱与获准后的Python进程，无在线模型。

```bash
python3 examples/s16-team-protocols/user_code/practice.py --decision allow
python3 examples/s16-team-protocols/user_code/practice.py --plan reject --decision allow
python3 examples/s16-team-protocols/user_code/practice.py
python3 examples/s16-team-protocols/user_code/verify_practice.py
python3 examples/s16-team-protocols/user_code/verify_fixtures.py
.venv/bin/python examples/s16-team-protocols/user_code/verify_sdk.py
```

reader提交固定计划，Lead用review_plan给出决定；保存回复后仍pending，接收方consume_responses匹配ID/类型/信封角色及已保存决定后，才approved/rejected。reader复用原历史，read_file读取expected、run_main先经本次plan_gate，再走原权限/Hook。计划批准和--decision独立，默认拒绝运行。允许路径真实输出42；拒绝计划即使allow也不能运行，批准计划而deny仍不能运行。7逻辑请求；SDK三路径分别8模拟HTTP（含一次529），4封信、程序最多一次。

Lead随后由宿主请求shutdown，成员空闲边界reply_request，保存确认后本地status=closed，Lead匹配前请求仍pending，匹配后approved。关闭成员再交付unavailable。忙碌时确认返回deferred，不杀线程；真实Event测试覆盖。此入口顺序驱动边界，不新增无限idle轮询/自动调度，不启其他Codex会话。

三个函数：[open_request / reply_request / match_response](core/README.md)。请求4条会话额度、同方向同类最多1条pending、正文180字符、反馈120字符；复用s15收件箱8条/600字符/32000字节，日志不删除。单进程RLock包含发送与内存登记的短段；磁盘保存失败不登记pending、不确认关闭；非跨进程事务或崩溃恢复。相同决定重复回复already_sent，冲突拒绝；匹配重放duplicate，未知ID/类型/角色/未保存决定ignored，不改状态。

计划绑定本次request_id、sender和不可改的正文；run_main仍是受限固定命令，批准不是任意执行授权。成员角色由宿主工具闭包绑定，模型不能填sender。这里是本地协作约定，不是密码学认证。超时/取消/新版本方案需新协议状态，不把旧同意迁移到新计划；本例无超时，不收到回复就保持pending，容量阻止无限增长。

默认临时目录清理；--maildir可保存邮箱但必须为空。请求状态和成员历史在内存，不从JSONL恢复。22同源浏览器教学输入、11标准库测试；浏览器虚拟文件原样执行三个函数，存储失败由公开故障替身注入，不执行SDK或进程。
