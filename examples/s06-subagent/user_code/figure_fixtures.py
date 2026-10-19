"""完整函数原样执行；原循环同源，模型与文件工具为公开、可查看的内存教学替身。"""
import inspect
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import child_tools,run_subagent,task_result,run_loop
FUNCTIONS=(child_tools,run_subagent,task_result)
CASES={'child_tools':['normal','missing'], 'run_subagent':['answered','limit','invalid','forbidden'],
       'task_result':['answered','limit','long']}


def fixture_context(name,scenario):
    if scenario not in CASES[name]:raise ValueError('unknown scenario')
    setup='''from copy import deepcopy
import json
from types import SimpleNamespace
QUESTION="教学默认问题"
scenario=SCENARIO
tools={name:{"parameters":{},"run":lambda:None} for name in ("read_file","run_main","task","todo_write")}
if scenario=="missing":tools.pop("read_file")
task="读取 main.py，说明源码推导；不要运行。"
if scenario=="invalid":task=" "
call={"id":"parent_task_1"}
outcome={"status":"answered","text":"源码推导42；尚未运行。","calls":3,"messages":[{"role":"user","content":"子任务内部记录"}]}
if scenario=="limit":outcome.update(status="call_limit",text="已达子循环预算，尚未得出结论。",calls=1)
if scenario=="long":outcome["text"]="长"*1201
# 明确替代模型和文件接口，未调用SDK或真实文件。
def ask(history,restricted):
    index=sum(item["role"]=="assistant" for item in history)
    if scenario=="forbidden" and index>0:
        return {"stop_reason":"end_turn","content":[{"type":"text","text":history[-1]["content"][0]["content"]}]}
    if index<2:
        name="run_main" if scenario=="forbidden" else "read_file"
        return {"stop_reason":"tool_use","content":[{"type":"tool_use","id":"child_"+str(index),"name":name,"input":{"path":"main.py" if index==0 else "expected.txt"}}]}
    return {"stop_reason":"end_turn","content":[{"type":"text","text":"源码推导42；尚未运行。"}]}
def execute_hooked(call,restricted,approve,hooks):
    name=call["name"]
    text="print(6 * 7)" if call["input"].get("path")=="main.py" else "42"
    return {"result":{"type":"tool_result","tool_use_id":call["id"],"content":text if name in restricted else "未执行：未注册工具。","is_error":name not in restricted},"warnings":[]}
_s04=SimpleNamespace(execute_hooked=execute_hooked,audit_event=lambda *args:None)
'''.replace('SCENARIO',repr(scenario))
    if name=='run_subagent':setup+='\n'+inspect.getsource(child_tools)+'\n'+inspect.getsource(run_loop)
    entry=f'''try:
    observed={"child_tools(tools)" if name=="child_tools" else "run_subagent(task,tools,ask,max_calls=1 if scenario=='limit' else 3,emit=lambda _:None)" if name=="run_subagent" else "task_result(call,outcome)"}
    print("完成：",observed.get("status",observed.get("content","只读工具已选出")))
except ValueError as error:
    observed={{"error":str(error)}}
    print(str(error))'''
    watch={'child_tools':['tools','name','selected','observed'],
           'run_subagent':['task','max_calls','restricted','outcome','observed'],
           'task_result':['status','text','failed','payload','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
