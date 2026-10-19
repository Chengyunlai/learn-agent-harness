# 第十四课：Cron Scheduler

先运行公开入口，再读core。Python3.10+，仅标准库；固定模型，真实文件和获准进程，没有在线模型调用。

```bash
python3 examples/s14-cron-scheduler/user_code/practice.py --decision allow
python3 examples/s14-cron-scheduler/user_code/practice.py --decision deny
python3 examples/s14-cron-scheduler/user_code/practice.py --serve-seconds 1
python3 examples/s14-cron-scheduler/user_code/verify_practice.py
python3 examples/s14-cron-scheduler/user_code/verify_fixtures.py
.venv/bin/python examples/s14-cron-scheduler/user_code/verify_sdk.py
```

默认是注入时钟：09:00:01入队1、同分钟09:00:40入队0、09:05入队1，busy不消费，空闲后交付两次独立run_loop。允许两次真实执行输出42，拒绝两次都不运行。每次模型3轮、s11父请求有界恢复；answered只说明收到回答。默认没有等待真实五分钟。

--serve-seconds 0到65，显式启用本进程真实时钟：一个可停止的非daemon调度线程每0.2秒检查，一个主线程空闲时交付。创建当分钟符合即可能触发；不是总等到下一个整分钟。退出stop/join，不安装操作系统计划或后台服务。

三个完整函数：cron_matches→enqueue_due→dispatch_next，见[符号映射](core/README.md)。时间固定UTC+08:00、无夏令时；五字段仅*和单值，分钟额外支持*/1至*/59，星期0周日，不接受范围/列表/7。*/N按分钟刻度匹配，不承诺每N分钟均匀间隔。日/星期都限制时OR，月/小时/分钟仍AND。非法输入注册时拒绝。

最多创建4张表（取消也不返还额度），队列8项、最近结果8项；同一RLock保护登记/队列/active。入队成功后才写last_slot；满时本分钟仍可重试，但错过的分钟不补发。UTC分钟ID跨日期，旧时刻不重复。一次性任务入队后移除表，未交付事件仍在；取消移除表及待交付项，不终止已经占用的轮次。

dispatch锁内先占用一项，锁外运行原循环，最终锁内保存结果并释放active。失败或中断记录，不自动重跑；单进程串行消费，无崩溃恰好一次保证。会话表/队列不落盘，退出即丢；不与s12持久任务或s13进程结果混同。沿s13的唯一原循环导出复用s10提示/s11恢复/旧工具权限与Hook；本课交付的是新问题，执行仍用同步run_main，后台启动另在s13可运行，本课不堆叠它。

build_schedule_tools给出schedule_cron/list_crons/cancel_cron注册，时间表可由宿主或显式暴露的模型工具管理。默认演示由宿主登记，不假装模型已经读懂自然语言时间。适配器不默认开放给每个定时轮次；加入注册时还须显式配置该内存工具的宿主权限（原默认拒绝未知工具策略）。

18浏览器输入原样执行函数/日期转换/锁；时钟注入，run_turn是可查看的回调替身，没有浏览器线程、进程或模型。12标准库测试覆盖真实并发生产/单消费者、真实程序计数、取消与队列满、失败释放。SDK1.13.0模拟HTTP允许4次含529、拒绝3次，不重复进程。配套文章在独立站点发布。
