# 第六课实现记录（2026-10-19）

编辑卡：已理解循环、工具、权限、Hook、清单的Python读者；用“检查main.py与expected，再获准运行”区分子探索与父判断。验证父历史无子文件正文、子工具无run/task/todo、失败保持ID。参考课程https://learn.shareai.run/zh/s06/与官方https://code.claude.com/docs/en/sub-agents（2026-10-19）；新上下文、工具范围和摘要回传有官方依据，具体Python与限制是本项目实现。

三个关键函数child_tools→run_subagent→task_result，循环复用第一课，不复制模型协议判断。同步一层、read_file白名单，单独模型请求预算，结论1200字符上限，失败/截断不冒充完成。父仍保留第五课工具与请求状态入口，默认脚本不冗余重演计划更新。

实际验证：verify_practice 31断言，真实临时文件/程序标记、父子历史隔离、白名单深复制、越权和递归拒绝、预算/model_error/超长返回与关联ID。verify_fixtures 9组绑定；站点正式trace_code采集74帧，源码和嵌套循环原样，仅模型/文件为内存替身，无外部请求。Anthropic1.13.0模拟HTTP允许/拒绝各7请求，通过父子system/tools和父结果核对。未运行在线模型。

提交关系：此提交为站点第六课按固定hash提取源函数与绑定的公开源版本；站点另记文章/图形的提交。CI继续跑前五课，增加s06离线和SDK验证。
