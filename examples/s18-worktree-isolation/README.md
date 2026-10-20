# 第十八课：Worktree Isolation

Python3.10+与Git，默认标准库。先运行user_code，再按core符号阅读。

```bash
python3 examples/s18-worktree-isolation/user_code/practice.py --decision allow
python3 examples/s18-worktree-isolation/user_code/practice.py
python3 examples/s18-worktree-isolation/user_code/verify_practice.py
python3 examples/s18-worktree-isolation/user_code/verify_fixtures.py
# 可选：安装根requirements后，用该虚拟环境运行verify_sdk.py
```

固定模型，真实临时Git仓库、两条队友线程、任务JSON和获准后的Python进程；没有在线模型。两个任务都改main.py，alpha写print(6*7)，beta写print(40+3)，分别输出42/43，主目录保持print(0)。复用s17自主认领、s15独立历史/交付、s10提示/s11恢复和唯一原run_loop；每成员一轮/最多4逻辑请求，共6次固定逻辑请求。工具写入和运行均要求本次--decision allow，未知工具仍默认拒绝；原Hook可选guard接入本课写策略，没有修改旧权限API。

create_workspace先为pending任务创建codex/<ID>分支和独立目录，再登记会话内绑定，不改变任务状态；以创建时实际HEAD提交为起点，不复制主目录未提交/未跟踪文件。工作树容器必须在主目录外，ID仅小写字母数字短横线、32字符、最多4绑定。任务和绑定仍是独立记录；不向旧任务格式塞入新字段。

workspace_for_task在共享RLock内核对最新in_progress/owner、登记路径、Git公共目录和分支；active=True预留本轮目录。run_teammate与工具在锁外工作，路径通过闭包绑定，subprocess有显式cwd，不使用os.chdir。调用者finally释放active，join后收尾。固定write_variant只写main.py且拒绝该文件符号链接；不是任意文件编辑器。路径和owner来自宿主，不接受模型传入。

retire_workspace接受keep/remove，不自动完成任务或合并。活跃目录返回busy；keep直接保留。remove检查跟踪/未跟踪/被忽略文件和HEAD是否仍等于创建提交；有任何内容或提交变化返回needs_review，默认保留待审。干净且HEAD未变才调用无--force的Git remove，分支仍保留。失败不假标记removed，不提供丢弃入口。

--state-dir必须为空，可保留真实Git目录与任务供人工检查；默认临时目录会在示例进程结束时整体清理。临时演示中的kept只表示收尾函数保留；要继续review必须显式用--state-dir。bindings和成员历史只在内存，没有跨进程恢复。所有本例状态写使用同一RLock；Git自身管理锁不能替代应用的认领锁。Git创建/删除与内存登记不是事务，超时或进程崩溃时需git worktree list --porcelain核查，不盲目强删或重试。工作树共享Git对象/refs，不是文件系统沙箱；程序仍有宿主权限，共享端口/数据库不隔离；两个分支合并时仍可能冲突。

14组真实Git测试覆盖两目录、拒绝、脏主目录不复制、并发唯一创建、owner/active、仅未跟踪或ignored文件保护、已提交结果、干净移除保留分支与任务、换分支/路径穿越/符号链接、创建/删除失败，以及后续真实合并冲突。19同源教学绑定公开Git与任务读取内存替身，浏览器不调用Git、不启动进程。SDK1.13.0允许/拒绝各7模拟HTTP（6逻辑请求+一次529），有工具反馈后的请求恢复不重复写入；无在线模型。
