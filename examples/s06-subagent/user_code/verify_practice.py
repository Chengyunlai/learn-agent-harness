"""真实文件/进程与父子消息协议，含能力越界、预算与摘要失败。"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from practice import run,child_model,use,answer
from runtime import child_tools,run_subagent,task_result,build_tools,execute_with_subagent
checks=0
def check(value):
    global checks
    assert value
    checks+=1
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    (root/'main.py').write_text('print(6 * 7)\n');(root/'expected.txt').write_text('42\n')
    for allowed in (False,True):
        out,traces,state=run(root,allowed,emit=lambda _:None)
        check(out['status']=='answered')
        check(('exit_code=0' in out['text'])==allowed)
        check(len(traces)==1 and traces[0]['status']=='answered')
        result=out['messages'][2]['content'][0]
        check(result['tool_use_id']=='step_1' and not result['is_error'])
        payload=json.loads(result['content']);check(set(payload)=={'status','summary','calls'})
        check('messages' not in result['content'] and 'print(6 * 7)' not in result['content'])
        check(len(traces[0]['messages'])==6 and len(out['messages'])==8)
    out,traces,_=run(root,True,child_calls=1,emit=lambda _:None)
    check(traces[0]['status']=='call_limit' and out['messages'][2]['content'][0]['is_error'])
    check('run_main' not in str(out['messages'][1:]))
    state={'items':[]};tools=build_tools(root,state,child_model)
    check(set(child_tools(tools))=={'read_file'})
    selected=child_tools(tools);selected['read_file']['parameters']['path']=int
    check(tools['read_file']['parameters']['path'] is str)
    seen=[]
    def observe(history,restricted):
        seen.append(deepcopy(history));check(set(restricted)=={'read_file'});return answer('尚未运行。')
    run_subagent('任务A',tools,observe,emit=lambda _:None)
    run_subagent('任务B',tools,observe,emit=lambda _:None)
    check(seen==[[{'role':'user','content':'任务A'}],[{'role':'user','content':'任务B'}]])
    marker=root/'ran'
    (root/'main.py').write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n")
    def malicious(history,restricted):
        if len(history)==1:return use('run_main',{},1)
        check(history[-1]['content'][0]['is_error']);return answer('未运行。')
    run_subagent('试图越权',tools,malicious,emit=lambda _:None)
    check(not marker.exists())
    def recurse(history,restricted):return use('task',{'task':'再委派'},1)
    out=run_subagent('尝试递归',tools,recurse,max_calls=1,emit=lambda _:None)
    check(out['status']=='call_limit' and out['messages'][-1]['content'][0]['is_error'])
    def broken(*_):raise RuntimeError('offline')
    out=run_subagent('网络故障',tools,broken,emit=lambda _:None)
    check(out['status']=='model_error')
    check(task_result({'id':'parent'},out)['is_error'])
    report=execute_with_subagent({'id':'p','name':'task','input':{'task':' '}},tools,lambda *_:True,{})
    check(report['result']['is_error'] and report['result']['tool_use_id']=='p')
    long=task_result({'id':'p'},{'status':'answered','text':'x'*1201,'calls':1,'messages':['private']})
    check(long['is_error'] and 'private' not in long['content'])
    for allowed in (False,True):
        if marker.exists():marker.unlink()
        out,_,_=run(root,allowed,emit=lambda _:None)
        check(marker.exists()==allowed)
    out,_,_=run(root,True,parent_calls=1,emit=lambda _:None)
    check(out['status']=='call_limit')
print('PASS',checks,'subagent assertions; real file/process and separate histories')
