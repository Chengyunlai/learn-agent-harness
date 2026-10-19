"""三个函数原样运行；句柄替身显式给出进程快照，不实际启动进程。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import start_background, collect_background, prepare_background
FUNCTIONS = (start_background, collect_background, prepare_background)
CASES = {'start_background': ['start', 'denied', 'invalid', 'duplicate', 'full', 'launch_error'],
         'collect_background': ['running', 'success', 'failure', 'timeout', 'cached'],
         'prepare_background': ['new', 'already', 'pending', 'discarded']}


def fixture_context(name, case):
    if case not in CASES[name]:
        raise ValueError('unknown case')
    setup = "from copy import deepcopy\nimport json\n"
    for fn in FUNCTIONS:
        setup += inspect.getsource(fn) + "\n"
    setup += """
class TeachingHandle:
    def __init__(self, result=None):
        self.result = result
        self.checks = 0
    def snapshot(self):
        self.checks += 1
        return deepcopy(self.result)
scenario = SCENARIO
name = FUNCTION
jobs = {}
call = {'id': 'call_1', 'name': 'run_background', 'input': {}}
allowed = scenario != 'denied'
launched = []
finished = {'status': 'completed', 'exit_code': 0, 'output': '42', 'is_error': False}
if scenario == 'failure':finished.update(exit_code=1, output='ZeroDivisionError', is_error=True)
if scenario == 'timeout':finished.update(status='timeout', exit_code=-9, output='', is_error=True)
def launch():
    if scenario == 'launch_error':raise OSError('教学启动失败')
    launched.append('main.py')
    return TeachingHandle()
if scenario == 'invalid':call['input'] = {'command': 'other'}
if name != 'start_background' or scenario in ('duplicate', 'full'):
    start_background(call, jobs, launch, True)
if scenario == 'full':
    for i in range(2, 5):start_background({**call, 'id': 'call_'+str(i)}, jobs, launch, True)
    call['id'] = 'call_5'
if name != 'start_background' and scenario not in ('running', 'pending'):
    jobs['call_1']['handle'].result = finished
if scenario == 'cached':collect_background(jobs)
history = [{'role': 'user', 'content': '后台运行main.py。'},
           {'role': 'assistant', 'content': [{'type': 'tool_use', **call}]},
           {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'call_1', 'content': 'started'}]}]
if scenario == 'already':history = prepare_background(history, jobs)
if scenario == 'discarded':prepare_background(history, jobs)
before = deepcopy(history)
""".replace('SCENARIO', repr(case)).replace('FUNCTION', repr(name))
    call_text = {'start_background': 'start_background(call, jobs, launch, allowed)',
                 'collect_background': 'collect_background(jobs)',
                 'prepare_background': 'prepare_background(history, jobs)'}[name]
    entry = 'observed = ' + call_text + '\nassert history == before\nprint(observed)\n'
    watch = {'start_background': ['call', 'job_id', 'text', 'launched', 'observed'],
             'collect_background': ['call_id', 'snapshot', 'completed', 'observed'],
             'prepare_background': ['event', 'text', 'present', 'candidate', 'observed']}[name]
    return {'setup': setup, 'entry': entry, 'watch': watch, 'scopes': [name]}
