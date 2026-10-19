"""原样函数、真实临时虚拟文件；替换失败情形仅注入公开故障接口。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import validate_memory, validate_records, load_memory, memory_catalog, checked_catalog, save_memory, select_memories, prepare_memory
FUNCTIONS = (save_memory, select_memories, prepare_memory)
CASES = {'save_memory': ['new', 'update', 'unapproved', 'invalid', 'replace_error'],
         'select_memories': ['match', 'none', 'limit', 'invalid'],
         'prepare_memory': ['selected', 'none', 'unknown', 'budget', 'current']}


def fixture_context(name, case):
    if case not in CASES[name]: raise ValueError('unknown case')
    setup = '''from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
scenario=SCENARIO
_temp=tempfile.TemporaryDirectory(prefix="lesson9-")
directory=Path(_temp.name)
report={"name":"report-format","description":"程序报告偏好","keywords":["核对","报告"],"body":"报告使用中文，先给核对结论，再列是否执行、退出码与证据。","source":"用户明确要求，宿主审核"}
sql={**report,"name":"sql-style","description":"SQL书写偏好","keywords":["SQL"],"body":"SQL关键字使用大写。"}
initial=[] if scenario=="new" else [report,sql]
(directory/"memory.json").write_text(json.dumps({"version":1,"records":initial},ensure_ascii=False),encoding="utf-8")
before_file=(directory/"memory.json").read_bytes()
'''.replace('SCENARIO', repr(case))
    for helper in (validate_memory, validate_records, load_memory, memory_catalog, checked_catalog):
        setup += '\n' + inspect.getsource(helper)
    setup += '''
records=load_memory(directory)
catalog=memory_catalog(records)
candidate={**report,"body":"更新后的报告偏好：先说明是否执行。"}
approved=scenario!="unapproved"
if scenario=="invalid":candidate["body"]=""
if scenario=="replace_error":
    _fsync=os.fsync
    def fail_replace(source,target):raise OSError("教学替换失败，旧文件保留")
    os=SimpleNamespace(fsync=_fsync,replace=fail_replace)
question="核对输出并报告"
if scenario=="none":question="介绍天气"
if scenario=="limit":question="核对并检查SQL"
if scenario=="current":question="本次用一句话报告"
if scenario=="invalid" and NAME=="select_memories":catalog[0]["body"]="目录不应带正文"
selected=["report-format"]
if scenario=="none":selected=[]
if scenario=="unknown":selected.append("missing")
messages=[{"role":"user","content":question},{"role":"assistant","content":[{"type":"tool_use","id":"run_1","name":"run_main","input":{}}]},{"role":"user","content":[{"type":"tool_result","tool_use_id":"run_1","content":"本次拒绝，未执行。","is_error":True}]}]
before=deepcopy(messages)
'''.replace('NAME', repr(name))
    call = {'save_memory': 'save_memory(directory,candidate,approved)', 'select_memories': 'select_memories(catalog,question,max_items=1 if scenario=="limit" else 2)', 'prepare_memory': 'prepare_memory(messages,records,selected,max_bytes=10 if scenario=="budget" else 4096)'}[name]
    entry = 'try:\n    observed=' + call + '\n    print("返回：",observed)\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\n    print(str(error))\nassert messages==before\n'
    if name == 'prepare_memory':
        entry = entry.replace('print("返回：",observed)', 'print("本次请求副本已准备；原历史保持不变。")')
    if name == 'save_memory':
        entry += 'stored=load_memory(directory)\nprint("当前保存：",[item["name"] for item in stored])\n'
        if case in ('unapproved', 'invalid', 'replace_error'):entry += 'assert (directory/"memory.json").read_bytes()==before_file\n'
    watch = {'save_memory': ['item', 'records', 'replacement', 'observed'],
             'select_memories': ['query', 'selected', 'item', 'matched', 'observed'],
             'prepare_memory': ['selected', 'notes', 'prepared', 'observed']}[name]
    return {'setup': setup, 'entry': entry, 'watch': watch, 'scopes': [name]}
