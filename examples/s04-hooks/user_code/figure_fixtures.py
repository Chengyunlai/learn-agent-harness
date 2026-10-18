"""原样函数正文；工具/宿主为公开替身，hook 回调与异常真实执行。"""
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import run_hooks, execute_hooked, audit_event, _s03
FUNCTIONS=(run_hooks,execute_hooked,audit_event)
CASES={'run_hooks':['pass','block','pre_error','post_error'],
       'execute_hooked':['pass','block','refused','post_error','mutate'],
       'audit_event':['before','after','rejected']}


def fixture_context(name,scenario):
    if scenario not in CASES[name]: raise ValueError('unknown scenario')
    setup=f'''from copy import deepcopy
scenario={scenario!r}
entries=[]
visited=[]
_executions=[]
_approvals=[]
call={{"type":"tool_use","id":"run_1","name":"run_main","input":{{}}}}
def _run():
    _executions.append("run_main")
    return "exit_code=0\\n42"
tools={{"run_main":{{"parameters":{{}},"run":_run}}}}
def ask_user(shown,reason):
    _approvals.append(shown)
    return scenario!="refused"
def first(payload):
    visited.append("first")
    if scenario=="block":return "维护期间暂停运行。"
    if scenario in ("pre_error","post_error"):raise OSError("审计不可用")
    if scenario=="mutate":
        payload["call"].update(id="changed",name="unknown")
        payload.get("result",{{}}).update(content="fake")
def second(payload):
    visited.append("second")
hooks={{"before":[first,second],"after":[second]}}
event="after" if scenario=="post_error" else "before"
payload={{"call":call}}
'''
    helpers=(_s03.validate_call,_s03.execute_tool,_s03.permission_for,_s03.authorize_call,_s03.execute_guarded,run_hooks)
    for helper in helpers:
        if helper.__name__!=name:setup+='\n'+inspect.getsource(helper)
    if name=='run_hooks':
        if scenario=='post_error':setup+='\nhooks["after"]=[first,second]\n'
        entry='outcome=run_hooks(hooks,event,payload)\nprint("回调顺序："+" → ".join(visited))'
        watch=['event','reason','warnings','message','outcome','index']
    elif name=='execute_hooked':
        if scenario=='post_error':setup+='\nhooks={"before":[second],"after":[first,second]}\n'
        entry='outcome=execute_hooked(call,tools,ask_user,hooks)\nprint("实际执行："+("、".join(_executions) or "无"))'
        watch=['snapshot','before','result','after','outcome']
    else:
        setup+='\nevent="before" if scenario=="before" else "after"\npayload["result"]={"is_error":scenario=="rejected","content":"未执行：用户拒绝" if scenario=="rejected" else "exit_code=0\\n42"}\n'
        entry='audit_event(event,payload,entries)\noutcome=entries\nprint("审计条目："+str(len(entries)))'
        watch=['event','call','entry','result','entries','outcome']
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}


if __name__=='__main__':
    print(json.dumps({f.__name__:{case:fixture_context(f.__name__,case) for case in CASES[f.__name__]} for f in FUNCTIONS},ensure_ascii=False))
