"""计划函数正文在浏览器真实执行，无模型、文件或进程调用。"""
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import validate_todos,write_todos,prepare_messages,format_todos
FUNCTIONS=(validate_todos,write_todos,prepare_messages)
CASES={'validate_todos':['valid','duplicate','active','unknown'],
       'write_todos':['replace','invalid','clear','claim'],
       'prepare_messages':['pending','updated','empty']}


def fixture_context(name,scenario):
    if scenario not in CASES[name]:raise ValueError('unknown scenario')
    setup=f'''from copy import deepcopy
scenario={scenario!r}
state={{"items":[{{"id":"1","content":"读取源码","status":"completed"}},{{"id":"2","content":"运行并核对","status":"pending"}}]}}
items=[{{"id":"1","content":"读取源码","status":"completed"}},{{"id":"2","content":"运行并核对","status":"in_progress"}}]
if scenario=="duplicate":items[1]["id"]="1"
if scenario in ("active","invalid"):items[0]["status"]="in_progress"
if scenario=="unknown":items[1]["status"]="done"
if scenario in ("clear","empty"):items=[]
if scenario=="claim":
    for item in items:item["status"]="completed"
messages=[{{"role":"user","content":"读文件，获准后运行并核对。"}},{{"role":"assistant","content":[{{"type":"tool_use","id":"run_1","name":"run_main","input":{{}}}}]}},{{"role":"user","content":[{{"type":"tool_result","tool_use_id":"run_1","content":"未执行：用户拒绝。","is_error":True}}]}}]
if scenario=="updated":state["items"][1]["status"]="completed"
if scenario=="empty":state["items"]=[]
'''
    for helper in [validate_todos,format_todos]:
        if helper.__name__!=name:setup+='\n'+inspect.getsource(helper)
    if name=='validate_todos':
        entry='''try:
    outcome=validate_todos(items)
    print("校验通过")
except ValueError as error:
    outcome={"error":str(error)}
    print(str(error))'''
        watch=['normalized','seen','active','key','status','outcome']
    elif name=='write_todos':
        entry='''try:
    outcome=write_todos(state,items)
except ValueError as error:
    outcome={"error":str(error)}
print("当前清单：")
print(format_todos(state["items"]))'''
        watch=['state','items','replacement','rendered','outcome']
    else:
        entry='outcome=prepare_messages(messages,state)\nprint("原问题保持不变；本次请求附带当前清单。")'
        watch=['messages','state','prepared','current','outcome']
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}


if __name__=='__main__':print(json.dumps({f.__name__:{case:fixture_context(f.__name__,case) for case in CASES[f.__name__]} for f in FUNCTIONS},ensure_ascii=False))
