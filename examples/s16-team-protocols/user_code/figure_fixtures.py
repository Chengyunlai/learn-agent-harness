"""同源函数与真实虚拟邮箱；只在指定场景注入保存故障。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import runtime as core
FUNCTIONS=(core.open_request,core.reply_request,core.match_response)
CASES={'open_request':['plan','shutdown','direction','pending','limit','save_error'],
       'reply_request':['approve','reject','wrong_role','busy','closed','duplicate','conflict','save_error'],
       'match_response':['approved','rejected','wrong_type','wrong_role','unknown','invalid','duplicate','forged']}


def fixture_context(name, case):
    if case not in CASES[name]:raise ValueError('unknown input')
    setup='from copy import deepcopy\nfrom pathlib import Path\nfrom threading import RLock\nimport json\nimport re\nimport os\nimport tempfile\nPREFIX="[team-protocol] "\n'
    for fn in (core.member_name,core.load_inbox,core._s15.save_inbox,core.send_message,core.create_team,core.encode_protocol,core.read_protocol,*FUNCTIONS):
        setup+=inspect.getsource(fn)+'\n'
    setup+="""
scenario=SCENARIO
state,team,lock={},create_team(),RLock()
_temp=tempfile.TemporaryDirectory(prefix='s16-mail-');directory=Path(_temp.name)
sender,target,kind,payload='reader','lead','plan','读取预期，再运行main.py。'
actor,approve,feedback='lead',True,'仅批准本次计划，权限另行判断。'
if FUNCTION!='open_request':
    kind='shutdown' if scenario in ('busy','closed') else 'plan'
    sender,target=('lead','reader') if kind=='shutdown' else ('reader','lead')
    if kind=='shutdown':payload,feedback='本次工作结束，请在空闲边界关闭。','空闲边界确认本次关闭。'
    request_id=open_request(state,team,directory,sender,target,kind,payload,lock)['request_id']
    actor=target
if FUNCTION=='open_request':
    if scenario=='shutdown':sender,target,kind,payload='lead','reader','shutdown','本次工作结束，请在空闲边界关闭。'
    if scenario=='direction':sender,target='lead','reader'
    if scenario=='pending':open_request(state,team,directory,sender,target,kind,payload,lock)
    if scenario=='limit':
        for i in range(4):state['old-'+str(i)]={'status':'rejected'}
if scenario in ('reject','rejected'):approve=False
if FUNCTION=='reply_request':
    if scenario=='wrong_role':actor='reviewer'
    if scenario=='busy':team['reader'].update(active=True,status='running')
    if scenario in ('duplicate','conflict'):
        reply_request(state,team,directory,request_id,actor,True,feedback,lock)
        if scenario=='conflict':approve=False
if FUNCTION=='match_response':
    reply_request(state,team,directory,request_id,actor,approve,feedback,lock)
    message=deepcopy(load_inbox(directory,sender,team)[-1]);recipient=sender
    data=read_protocol(message)
    if scenario=='wrong_type':data['type']='shutdown_response'
    if scenario=='wrong_role':message['sender']='reviewer'
    if scenario=='unknown':data['request_id']='req-404'
    if scenario=='invalid':data['approve']='true'
    if scenario=='forged':data['feedback']='不同的未保存决定'
    message['body']=encode_protocol(data)
    if scenario=='duplicate':match_response(state,message,recipient,lock)
before=deepcopy(state)
_replace=os.replace
def broken_replace(*_):raise OSError('教学保存失败')
if scenario=='save_error':os.replace=broken_replace
""".replace('SCENARIO',repr(case)).replace('FUNCTION',repr(name))
    call={'open_request':'open_request(state, team, directory, sender, target, kind, payload, lock)',
          'reply_request':'reply_request(state, team, directory, request_id, actor, approve, feedback, lock)',
          'match_response':'match_response(state, message, recipient, lock)'}[name]
    entry='try:\n    observed='+call+'\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\nfinally:\n    os.replace=_replace\nprint(observed)\n'
    watch={'open_request':['kind','request_id','request','receipt','state','observed'],
           'reply_request':['actor','record','response','state','team','observed'],
           'match_response':['recipient','data','record','state','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
