"""正式函数原样执行；真实Worker虚拟邮箱与锁，轮次回调为公开替身。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import member_name, load_inbox, save_inbox, create_team, send_message, prepare_inbox, run_teammate
FUNCTIONS = (send_message, prepare_inbox, run_teammate)
CASES = {'send_message': ['queued', 'unknown', 'sender', 'invalid', 'full', 'replace_error'],
         'prepare_inbox': ['new', 'already', 'discarded', 'empty', 'corrupt', 'limit'],
         'run_teammate': ['first', 'continued', 'busy', 'exhausted', 'failed', 'stopped']}


def fixture_context(name, case):
    if case not in CASES[name]:raise ValueError('unknown case')
    setup = "from copy import deepcopy\nfrom pathlib import Path\nfrom threading import RLock\nimport json\nimport os\nimport re\nimport tempfile\n"
    for fn in (member_name, load_inbox, save_inbox, create_team, *FUNCTIONS):
        setup += inspect.getsource(fn) + '\n'
    setup += """
scenario = SCENARIO
team, lock = create_team(), RLock()
_temp = tempfile.TemporaryDirectory(prefix='s15-mail-')
directory = Path(_temp.name)
sender, recipient, body = 'reviewer', 'reader', '当前expected.txt记录为42；尚未运行。'
history = [{'role': 'user', 'content': '保留上轮源码，等队友补充预期。'}]
if FUNCTION=='prepare_inbox' and scenario!='empty':send_message(directory,team,sender,recipient,body,lock)
if scenario=='already':history=prepare_inbox(history,directory,team,recipient,lock)
if scenario=='discarded':prepare_inbox(history,directory,team,recipient,lock)
if scenario=='corrupt':(directory/'reader.jsonl').write_text('not-json')
if scenario=='limit':history=[{'role':'user','content':'已存消息'+str(i)} for i in range(80)]
if scenario=='unknown':recipient='../other'
if scenario=='sender':sender='unknown'
if scenario=='invalid':body=''
if scenario=='full':
    for i in range(8):send_message(directory,team,sender,recipient,'旧记录'+str(i),lock)
name='reader'
if scenario=='continued':
    team[name]['history']=[{'role':'user','content':'先前读取main.py。'},{'role':'assistant','content':'已保存源码；没有运行。'}]
    team[name]['turns']=1
if scenario=='busy':team[name].update(active=True,status='running')
if scenario=='exhausted':team[name]['turns']=2
received=[]
def run_turn(previous):
    received.append(deepcopy(previous))
    if scenario=='failed':raise OSError('教学轮次失败')
    return {'status':'call_limit' if scenario=='stopped' else 'answered','text':'保存补充说明，仍没有运行。',
            'messages':previous+[{'role':'user','content':'本轮追问'},{'role':'assistant','content':'依据已有记录补充回答。'}]}
before=deepcopy(history)
old_mail=(directory/'reader.jsonl').read_bytes() if (directory/'reader.jsonl').exists() else None
_replace=os.replace
def broken_replace(*_):raise OSError('教学保存失败')
if scenario=='replace_error':os.replace=broken_replace
""".replace('SCENARIO',repr(case)).replace('FUNCTION',repr(name))
    call={'send_message':'send_message(directory, team, sender, recipient, body, lock)',
          'prepare_inbox':'prepare_inbox(history, directory, team, recipient, lock)',
          'run_teammate':'run_teammate(team, name, run_turn, lock)'}[name]
    entry='try:\n    observed='+call+'\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\nfinally:\n    os.replace=_replace\nassert history==before\nprint(observed)\n'
    watch={'send_message':['sender','recipient','items','message','observed'],
           'prepare_inbox':['items','message','present','candidate','observed'],
           'run_teammate':['name','team','member','history','outcome','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
