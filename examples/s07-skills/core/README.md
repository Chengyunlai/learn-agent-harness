# 符号映射

先跑../user_code/practice.py。正式实现唯一入口runtime.py：

- read_header(path)：有界读取并校验两字段头部，关闭文件前不解析正文。
- scan_skills(root)：扫描目录、检查路径与名称，形成description/path/root注册表。
- build_system(registry,base)：从固定base与名称/描述生成目录，正文不参与。
- load_skill(name,registry)：按名称定位路径，重检边界，完整有界UTF-8读取。
- build_tools：扩展s06工具表，load_skill只接收名称字符串。
- execute_with_skills：load_skill先过Hook再本地分发；其他仍s06。
- ask_claude：一次SDK调用，接收预先生成的system。

断点用scan_skills/build_system/load_skill符号；浏览器figure_fixtures按相同函数准备虚拟文件，read_header与scan_skills helper按inspect提取，未复制运行时逻辑。
