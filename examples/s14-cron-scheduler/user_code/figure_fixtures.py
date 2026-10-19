"""原样调度函数与真实日期/锁；时钟输入和轮次回调是显式教学替身。"""
from datetime import datetime
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import cron_fields, checked_time, new_state, schedule_job, cron_matches, enqueue_due, dispatch_next
FUNCTIONS = (cron_matches, enqueue_due, dispatch_next)
CASES = {'cron_matches': ['step', 'not_due', 'day_or', 'sunday', 'invalid', 'naive'],
         'enqueue_due': ['due', 'duplicate', 'full', 'once', 'backward', 'not_due'],
         'dispatch_next': ['ready', 'busy', 'active', 'empty', 'failed', 'model_stop']}


def fixture_context(name, case):
    if case not in CASES[name]: raise ValueError('unknown case')
    setup = "from copy import deepcopy\nfrom datetime import datetime, timedelta, timezone\nfrom threading import RLock\nimport re\nLOCAL=timezone(timedelta(hours=8))\n"
    for fn in (cron_fields, checked_time, new_state, schedule_job, *FUNCTIONS):
        setup += inspect.getsource(fn) + '\n'
    setup += """
scenario = SCENARIO
state, lock = new_state(), RLock()
expression = '*/5 * * * *'
when = datetime.fromisoformat('2026-10-19T09:05:23+08:00')
if scenario=='not_due':when=datetime.fromisoformat('2026-10-19T09:04:00+08:00')
if scenario=='day_or':expression='0 9 1 * 1';when=datetime.fromisoformat('2026-10-19T09:00:00+08:00')
if scenario=='sunday':expression='0 9 * * 0';when=datetime.fromisoformat('2026-10-18T09:00:00+08:00')
if scenario=='invalid':expression='*/0 * * * *'
if scenario=='naive':when=when.replace(tzinfo=None)
if FUNCTION!='cron_matches':
    schedule_job(state,lock,expression,'检查main.py，运行仍需本次许可。',once=scenario=='once')
    if FUNCTION=='dispatch_next' and scenario!='empty':enqueue_due(state,when,lock)
    if scenario=='duplicate':enqueue_due(state,when,lock)
    if scenario=='backward':
        enqueue_due(state,when,lock)
        when=datetime.fromisoformat('2026-10-19T09:00:00+08:00')
    if scenario=='full':state['queue']=[{'id':'earlier-'+str(i)} for i in range(8)]
    if scenario=='active':state['active']='another-turn'
received=[]
def run_turn(event):
    received.append(deepcopy(event))
    if scenario=='failed':raise OSError('教学轮次失败')
    return {'status':'call_limit' if scenario=='model_stop' else 'answered','text':'模型已停下；程序是否成功需看执行证据。'}
busy=scenario=='busy'
""".replace('SCENARIO',repr(case)).replace('FUNCTION',repr(name))
    call={'cron_matches':'cron_matches(expression, when)', 'enqueue_due':'enqueue_due(state, when, lock)',
          'dispatch_next':'dispatch_next(state, run_turn, lock, busy)'}[name]
    entry='try:\n    observed='+call+'\nexcept ValueError as error:\n    observed={"error":str(error)}\nprint(observed)\n'
    watch={'cron_matches':['expression','parts','day_ok','week_ok','observed'],
           'enqueue_due':['state','slot','job','event','added','observed'],
           'dispatch_next':['state','busy','event','response','outcome','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
