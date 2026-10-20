"""原样函数；Git命令与看板读取为公开内存替身，不在浏览器创建真实工作树。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import runtime as core
FUNCTIONS = (core.create_workspace, core.workspace_for_task, core.retire_workspace)
CASES = {'create_workspace': ['new', 'duplicate', 'claimed', 'invalid', 'git_error', 'limit'],
         'workspace_for_task': ['owned', 'wrong_owner', 'pending', 'busy', 'branch_changed', 'removed'],
         'retire_workspace': ['keep', 'clean', 'dirty', 'committed', 'ignored', 'busy', 'remove_error']}


def fixture_context(name, case):
    if case not in CASES[name]: raise ValueError('unknown input')
    setup = 'from copy import deepcopy\nfrom pathlib import Path\nfrom threading import RLock\nimport re\n'
    for fn in (core.workspace_target, core.checked_workspace, *FUNCTIONS): setup += inspect.getsource(fn) + '\n'
    setup += """
scenario=SCENARIO
repo=Path('/teaching-s18/repo');parent=Path('/teaching-s18/worktrees');directory='board';lock=RLock();task_id='alpha';actor='reader'
base='a'*40;bindings={};commands=[];present={};changed=False;dirty_text='';fail_add=False;fail_remove=False
board={'tasks':{'alpha':{'id':'alpha','status':'pending','owner':None}}}
def load_board(_):return deepcopy(board)
def git(cwd,*args):
    key=str(cwd);commands.append(list(args))
    if args[:2]==('worktree','add'):
        if fail_add:raise ValueError('教学Git创建失败')
        present[args[4]]=args[3];return ''
    if args[:2]==('worktree','remove'):
        if fail_remove:raise ValueError('教学Git删除失败')
        present.pop(args[2]);return ''
    if args==('rev-parse','HEAD'):return ('b'*40 if changed and key!=str(repo) else base)
    if args==('rev-parse','--show-toplevel'):
        if key not in present:raise ValueError('工作树不在登记中')
        return key
    if args==('rev-parse','--git-common-dir'):return str(repo/'.git')
    if args==('branch','--show-current'):return 'unexpected' if scenario=='branch_changed' else present[key]
    if args[0]=='status':return dirty_text
    raise AssertionError('未知替身命令：'+str(args))
if FUNCTION!='create_workspace' or scenario=='duplicate':
    create_workspace(repo,parent,directory,bindings,task_id,lock)
if FUNCTION=='create_workspace':
    if scenario=='claimed':board['tasks']['alpha'].update(status='in_progress',owner='reader')
    if scenario=='invalid':task_id='../outside'
    if scenario=='git_error':fail_add=True
    if scenario=='limit':bindings.update({str(i):{} for i in range(4)})
if FUNCTION=='workspace_for_task':
    if scenario!='pending':board['tasks']['alpha'].update(status='in_progress',owner='reviewer' if scenario=='wrong_owner' else 'reader')
    if scenario=='busy':bindings['alpha']['active']=True
    if scenario=='removed':bindings['alpha']['status']='removed'
if FUNCTION=='retire_workspace':
    if scenario=='dirty':dirty_text=' M main.py'
    if scenario=='ignored':dirty_text='!! local-cache'
    if scenario=='committed':changed=True
    if scenario=='busy':bindings['alpha']['active']=True
    if scenario=='remove_error':fail_remove=True
commands.clear()
action='keep' if scenario=='keep' else 'remove'
""".replace('SCENARIO', repr(case)).replace('FUNCTION', repr(name))
    call = {'create_workspace': 'create_workspace(repo,parent,directory,bindings,task_id,lock)',
            'workspace_for_task': 'workspace_for_task(repo,parent,directory,bindings,task_id,actor,lock)',
            'retire_workspace': 'retire_workspace(repo,parent,bindings,task_id,action,lock)'}[name]
    entry = 'try:\n    observed=' + call + '\nexcept (ValueError,KeyError) as error:\n    observed={"error":str(error)}\nprint(observed)\n'
    watch = {'create_workspace': ['task_id','task','base','bindings','record','observed'],
             'workspace_for_task': ['actor','task','record','bindings','path','observed'],
             'retire_workspace': ['record','bindings','dirty','head','action','observed']}[name]
    return {'setup': setup, 'entry': entry, 'watch': watch, 'scopes': [name]}
