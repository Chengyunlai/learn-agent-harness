"""同源扫描/认领/空闲函数；真实Worker虚拟文件与锁，等待由公开回调注入。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import runtime as core
FUNCTIONS=(core.scan_ready,core.claim_next,core.idle_poll)
CASES={'scan_ready':['ready','blocked','unlocked','owned','invalid','empty'],
       'claim_next':['claimed','stale','busy','blocked','active','closed','limit','save_error'],
       'idle_poll':['task','shutdown','timeout','wakeup','busy','interrupted','bad_checks','shutdown_failure']}


def fixture_context(name,case):
    if case not in CASES[name]:raise ValueError('unknown input')
    setup='from copy import deepcopy\nfrom pathlib import Path\nfrom threading import RLock\nimport json\nimport re\nimport os\nimport tempfile\nPREFIX="[team-protocol] "\n'
    helpers=(core._tasks.identifier,core.checked_board,core.load_board,core._tasks.save_board,core._tasks.ready_ids,core.create_task,core.claim_task,core.complete_task,
             core.member_name,core.create_team,core.load_inbox,core._s16._s15.save_inbox,core.send_message,core._s16.encode_protocol,core.read_protocol,core.open_request,core.reply_request,core.shutdown_at_boundary,*FUNCTIONS)
    for fn in helpers:setup+=inspect.getsource(fn)+'\n'
    setup+="""
scenario=SCENARIO
_temp=tempfile.TemporaryDirectory(prefix='s17-auto-');root=Path(_temp.name);directory=root/'board';mail=root/'mail'
team,state,lock=create_team(),{},RLock();name='reader';checks=3;waits=[]
def make_jobs():
    create_task(directory,'source','读取源码','固定main.py',[])
    create_task(directory,'expected','读取预期','固定expected.txt',[])
    create_task(directory,'verify','核对输出','固定程序',['source','expected'])
if not (FUNCTION=='scan_ready' and scenario=='empty') and not (FUNCTION=='idle_poll' and scenario in ('timeout','wakeup','interrupted')):make_jobs()
if FUNCTION=='scan_ready':
    if scenario in ('blocked','unlocked','owned'):
        claim_task(directory,'source','reviewer')
        if scenario!='owned':claim_task(directory,'expected','reviewer')
    if scenario=='unlocked':
        complete_task(directory,'source','reviewer','print(6*7)')
        complete_task(directory,'expected','reviewer','42')
board=load_board(directory);before=deepcopy(board)
if scenario=='invalid':board['tasks']['verify']['blocked_by']=['missing']
if FUNCTION=='claim_next':
    if scenario=='stale':claim_task(directory,'expected','reviewer')
    if scenario=='busy':claim_task(directory,'source',name)
    if scenario=='blocked':
        claim_task(directory,'source','reviewer');claim_task(directory,'expected','reviewer')
    if scenario=='active':team[name].update(active=True,status='running')
    if scenario=='closed':team[name]['status']='closed'
    if scenario=='limit':team[name]['turns']=2
if FUNCTION=='idle_poll':
    if scenario in ('shutdown','shutdown_failure'):
        open_request(state,team,mail,'lead',name,'shutdown','本次结束，在空闲边界确认关闭。',lock)
        if scenario=='shutdown':team[name]['turns']=2
    if scenario=='busy':team[name].update(active=True,status='running')
    if scenario=='bad_checks':checks=0
def wait(seconds):
    waits.append(seconds)
    if scenario=='wakeup' and len(waits)==1:create_task(directory,'source','新到的源码任务','固定main.py',[])
    return scenario=='interrupted'
_replace=os.replace
def broken_replace(*_):raise OSError('教学保存失败')
if scenario in ('save_error','shutdown_failure'):os.replace=broken_replace
""".replace('SCENARIO',repr(case)).replace('FUNCTION',repr(name))
    call={'scan_ready':'scan_ready(board)','claim_next':'claim_next(directory, team, name, lock)',
          'idle_poll':'idle_poll(directory, team, state, mail, name, lock, wait, checks)'}[name]
    entry='try:\n    observed='+call+'\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\nfinally:\n    os.replace=_replace\nprint(observed)\n'
    if name=='claim_next':entry+='board=load_board(directory)\n'
    watch={'scan_ready':['board','task_id','task','ready','observed'],
           'claim_next':['name','team','board','ready','task','observed'],
           'idle_poll':['name','team','index','control','outcome','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
