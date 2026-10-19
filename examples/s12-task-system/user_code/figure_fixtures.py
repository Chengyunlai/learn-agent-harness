"""原样函数；Worker临时虚拟任务文件，替换故障仅作公开可查看注入。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import identifier,checked_board,load_board,save_board,ready_ids,create_task,claim_task,complete_task
FUNCTIONS=(create_task,claim_task,complete_task)
CASES={'create_task':['new','duplicate','missing','self','bad_id','replace_error'],
       'claim_task':['ready','blocked','taken','unknown'],
       'complete_task':['done','wrong_owner','pending','empty','replace_error']}

def fixture_context(name,case):
 if case not in CASES[name]:raise ValueError('unknown case')
 setup='''from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile
scenario=SCENARIO
_temp=tempfile.TemporaryDirectory(prefix='lesson12-')
directory=Path(_temp.name)
'''.replace('SCENARIO',repr(case))
 for fn in (identifier,checked_board,load_board,save_board,ready_ids,create_task,claim_task,complete_task):setup+='\n'+inspect.getsource(fn)
 setup+='''
create_task(directory,'check','检查文件','读取当前文件，不等于已经运行。',[])
create_task(directory,'run','运行并核对','取得本次许可和执行证据。',['check'])
create_task(directory,'report','报告已存结论','引用run记录，不自动重新运行。',['run'])
task_id='review' if FUNCTION=='create_task' else 'run'
owner='worker-a'
result='本次获准运行，exit_code=0，实际输出42。'
deps=['check']
if scenario not in ('blocked','pending') and FUNCTION!='create_task':
    claim_task(directory,'check',owner)
    complete_task(directory,'check',owner,'已读文件，尚未运行。')
if FUNCTION=='claim_task' and scenario=='taken':claim_task(directory,'run',owner)
if FUNCTION=='complete_task' and scenario!='pending':claim_task(directory,'run',owner)
if scenario=='duplicate':task_id='check'
if scenario=='missing':deps=['missing']
if scenario=='self':deps=['review']
if scenario=='bad_id':task_id='../other'
if scenario=='unknown':task_id='missing'
if scenario=='wrong_owner':owner='worker-b'
if scenario=='empty':result=''
before=(directory/'tasks.json').read_bytes()
_replace=os.replace
def broken_replace(*_):raise OSError('教学替换失败')
if scenario=='replace_error':os.replace=broken_replace
'''.replace('FUNCTION',repr(name))
 call={'create_task':"create_task(directory,task_id,'复查记录','只更新任务图，不执行程序。',deps)",'claim_task':'claim_task(directory,task_id,owner)','complete_task':'complete_task(directory,task_id,owner,result)'}[name]
 entry='try:\n    observed='+call+'\n    print(observed)\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\n    print(str(error))\n    assert (directory/"tasks.json").read_bytes()==before\nfinally:\n    os.replace=_replace\n'
 watch={'create_task':['item','board','candidate','observed'],'claim_task':['item','blocked','candidate','observed'],'complete_task':['task_id','item','before','candidate','unlocked','observed']}[name]
 return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
