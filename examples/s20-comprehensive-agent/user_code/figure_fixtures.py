"""原函数与原循环/恢复/Hook；模型、文件进程、压缩附件及连接为公开内存教学绑定。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import runtime as core
FUNCTIONS=(core.prepare_turn,core.dispatch_call,core.run_session)
CASES={'prepare_turn':['attached','empty','compact_error','bad_notices','oversize'],
       'dispatch_call':['builtin','external','denied','blocked','warning','unknown'],
       'run_session':['answered','limit','context_error','model_error','close_error','host_error','retry']}
def fixture_context(name,case):
    if case not in CASES[name]:raise ValueError('unknown input')
    s07,s10,s11=core._s07,core._s10,core._s11
    s04,s02=s07._s04,s07._s02;s03=s04._s03
    setup='from copy import deepcopy\nfrom types import SimpleNamespace\nimport json,math,time,random\nQUESTION="检查程序"\n'
    setup+='class RecoveryStopped(RuntimeError):pass\n'
    for fn in (s02.validate_call,s02.execute_tool,s03.permission_for,s03.authorize_call,s03.execute_guarded,s04.run_hooks,s04.execute_hooked,core._s19.result_text,core._s19.call_external,s10._s08.history_bytes,s11.checked_state,s11.classify_failure,s11.retry_delay,s11.request_with_recovery,core.run_loop,core.freeze_capabilities,*FUNCTIONS):setup+=inspect.getsource(fn)+'\n'
    setup+='''
_s10=SimpleNamespace(_s08=SimpleNamespace(history_bytes=history_bytes))
_s07=SimpleNamespace(_s02=SimpleNamespace(execute_tool=execute_tool),_s04=SimpleNamespace(execute_guarded=execute_guarded,execute_hooked=execute_hooked))
_s19=SimpleNamespace(call_external=call_external)
_s11=SimpleNamespace(request_with_recovery=request_with_recovery)
scenario=SCENARIO
history=[{'role':'user','content':'检查main.py，核对42。'}];original=deepcopy(history)
notices_log=[];invoked=[];closed=[];sent=[];approvals=[]
def compact(history):
    if scenario in ('compact_error','context_error'):raise ValueError('归档失败')
    return deepcopy(history)
def attach(messages):
    if scenario!='empty':messages[0]['content']+='\\n[项目记忆] 按本次输出核对。'
    if scenario=='oversize':messages[0]['content']+='x'*8001
    return messages
def notices():return ['x'*241] if scenario=='bad_notices' else ([] if scenario=='empty' else ['收到检查任务。'])
def program():invoked.append('run_main');return 'exit_code=0\\n42'
def remote(name,args):invoked.append(name);return {'content':[{'type':'text','text':'需要本次许可。'}],'isError':False}
def confirm(*_):approvals.append('asked');return scenario!='denied'
def before(_):return '前置阻止' if scenario=='blocked' else None
def after(_):
    if scenario=='warning':raise ValueError('观察故障')
tools={'run_main':{'description':'固定运行main.py','parameters':{},'run':program}}
pool={'definitions':[{'name':'run_main','description':'固定运行main.py','input_schema':{'type':'object','properties':{},'additionalProperties':False}}],
      'routes':{'mcp__docs__search_docs':{'server':'docs','remote':'search.docs','schema':{'properties':{'query':{'type':'string'}}},'invoke':remote}}}
snapshot={'builtins':tools,'pool':pool,'system':'按本次证据核对。'}
call={'type':'tool_use','id':'step_1','name':'mcp__docs__search_docs' if scenario=='external' else 'missing' if scenario=='unknown' else 'run_main','input':{'query':'运行许可'} if scenario=='external' else {}}
hooks={'before':[before],'after':[after]}
def capabilities():return snapshot
def prepare(history):return prepare_turn(history,compact,attach,notices)
def send(request):
    sent.append(deepcopy(request))
    if scenario=='model_error':raise ValueError('模型接口故障')
    if scenario=='retry' and len(sent)==2:return {'failure':{'status':529,'retry_after':'0'}}
    if len(sent)==1:return {'stop_reason':'tool_use','content':[call]}
    return {'stop_reason':'end_turn','content':[{'type':'text','text':'收到实际工具反馈。'}]}
def close():
    closed.append('closed')
    if scenario=='close_error':raise OSError('关闭故障')
'''.replace('SCENARIO',repr(case))
    # host_error is a normal exception from a trusted dispatch boundary, rather than a signal.
    if case=='host_error':setup+="def broken_dispatch(*args,**kwargs):raise RuntimeError('宿主分发故障')\n_s07._s04.execute_hooked=broken_dispatch\n"
    calls={'prepare_turn':'prepare_turn(history,compact,attach,notices)','dispatch_call':'dispatch_call(call,snapshot,confirm,hooks)','run_session':"run_session('检查main.py',capabilities,prepare,send,confirm,hooks,close,max_calls="+('1' if case=='limit' else '2')+")"}
    entry='try:\n    observed='+calls[name]+'\nexcept Exception as error:\n    observed={"error":str(error)}\n'
    entry+="print(observed)\n"
    watch={'prepare_turn':['canonical','messages','events','history','observed'],
           'dispatch_call':['fixed','current','handled','invoked','approvals','observed'],
           'run_session':['state','prepared','snapshot','outcome','recovery','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name,'before','ask','execute','guard'] if name!='prepare_turn' else [name]}
