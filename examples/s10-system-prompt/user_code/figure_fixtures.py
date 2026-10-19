"""真实函数与同源helper；临时工作目录和声明式工具注册，不调用模型/程序。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import collect_context, assemble_system_prompt, get_system_prompt, checked_context, TEMPLATES, _s09, _s07
FUNCTIONS=(collect_context,assemble_system_prompt,get_system_prompt)
CASES={'collect_context':['full','readonly','no_skill','invalid'],
       'assemble_system_prompt':['full','minimal','no_run','invalid'],
       'get_system_prompt':['cold','hit','changed','template','budget','invalid']}


def fixture_context(name,case):
    if case not in CASES[name]:raise ValueError('unknown case')
    setup='''from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
scenario=SCENARIO
_temp=tempfile.TemporaryDirectory(prefix="lesson10-")
workspace=Path(_temp.name)
TEMPLATES=TEMPLATE_VALUES
'''.replace('SCENARIO',repr(case)).replace('TEMPLATE_VALUES',repr(TEMPLATES))
    for fn in (_s09.validate_memory,_s09.validate_records,_s09.memory_catalog,_s09.checked_catalog):setup+='\n'+inspect.getsource(fn)
    setup+='\n'+inspect.getsource(_s07._s02.tool_definitions).replace('def tool_definitions(','def basic_definitions(',1)
    setup+='\n_s02=SimpleNamespace(tool_definitions=basic_definitions)\n'
    setup+='\n'+inspect.getsource(_s07._s05.tool_definitions).replace('def tool_definitions(','def plan_definitions(',1)
    setup+='''
_s09=SimpleNamespace(memory_catalog=memory_catalog,checked_catalog=checked_catalog)
_s07=SimpleNamespace(_s05=SimpleNamespace(tool_definitions=plan_definitions),_s02=SimpleNamespace(tool_definitions=basic_definitions))
tools={"read_file":{"description":"读取当前文件。","parameters":{"path":str},"run":lambda **_:None},"run_main":{"description":"运行固定main.py。","parameters":{},"run":lambda:None},"load_skill":{"description":"读取注册技能。","parameters":{"name":str},"run":lambda **_:None}}
skills={"output-check":{"description":"先读预期，再取得许可与本次证据。","path":"/not-read/SKILL.md"}}
memories=[{"name":"report-format","description":"先结论后证据的报告偏好","keywords":["核对"],"body":"先给核对结论，再列当前执行证据。","source":"用户明确要求"}]
'''
    # 缓存预热也执行同源函数；随后显示区重新编译的正文完全相同，不另写缓存算法。
    for fn in (checked_context,collect_context,assemble_system_prompt,get_system_prompt):
        setup+='\n'+inspect.getsource(fn)
    setup+='''
cache={}
context=collect_context(workspace,tools,skills,memories)
if scenario in ("hit","changed","template","budget","invalid") and FUNCTION=="get_system_prompt":get_system_prompt(context,cache)
if scenario in ("readonly","no_run","changed"):tools.pop("run_main")
if scenario in ("no_skill","minimal"):
    tools.pop("load_skill")
    memories=[]
if scenario=="minimal":tools.pop("run_main")
if scenario=="invalid" and FUNCTION=="collect_context":tools["read_file"]["run"]=None
if not (scenario=="invalid" and FUNCTION=="collect_context"):context=collect_context(workspace,tools,skills,memories)
if scenario=="invalid" and FUNCTION=="assemble_system_prompt":context["tools"].append(deepcopy(context["tools"][0]))
if scenario=="invalid" and FUNCTION=="get_system_prompt":context["tools"][0]["input_schema"]["bad"]=set()
if scenario=="template":TEMPLATES["identity"]+=" 新固定规则。"
if scenario=="budget":TEMPLATES["identity"]="规"*5000
before=deepcopy(cache)
'''.replace('FUNCTION',repr(name))
    call={'collect_context':'collect_context(workspace,tools,skills,memories)','assemble_system_prompt':'assemble_system_prompt(context)','get_system_prompt':'get_system_prompt(context,cache)'}[name]
    entry='try:\n    observed='+call+'\n'
    if name=='collect_context':entry+='    print("已收集：",list(observed))\n'
    if name=='assemble_system_prompt':entry+='    print("段落：",[item["id"] for item in observed])\n'
    if name=='get_system_prompt':entry+='    print("本地复用：",observed["reused"])\n    print("段落：",observed["section_ids"])\n'
    entry+='except (ValueError,OSError) as error:\n    observed={"error":str(error)}\n    print(str(error))\n'
    if case in ('invalid','budget') and name=='get_system_prompt':entry+='assert cache==before\n'
    watch={'collect_context':['definitions','skill_catalog','memory_catalog','observed'],
           'assemble_system_prompt':['names','sections','observed'],
           'get_system_prompt':['reused','sections','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
