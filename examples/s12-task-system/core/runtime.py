"""第十二课：单写者持久任务图；依赖、认领与完成分别校验。"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

_path=Path(__file__).resolve().parents[2]/'s11-error-recovery/core/runtime.py'
_spec=importlib.util.spec_from_file_location('s11_runtime',_path)
_s11=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_s11)
_s10=_s11._s10
_s07=_s10._s07
run_loop=_s10.run_loop


def identifier(value):
    if type(value) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,31}',value):
        raise ValueError('标识必须是1到32位小写字母、数字或连字符。')
    return value


def checked_board(board):
    if type(board) is not dict or set(board)!={'version','revision','tasks'} or type(board['version']) is not int or board['version']!=1 or type(board['revision']) is not int or not 0<=board['revision']<=10000:
        raise ValueError('任务文件版本或修订号无效。')
    tasks=board['tasks']
    if type(tasks) is not dict or len(tasks)>20:
        raise ValueError('最多保存20项任务。')
    for key,item in tasks.items():
        identifier(key)
        if type(item) is not dict or set(item)!={'id','subject','description','status','owner','blocked_by','result'} or item['id']!=key:
            raise ValueError('任务字段或ID不一致。')
        for field,limit in [('subject',120),('description',600),('result',1200)]:
            if type(item[field]) is not str or len(item[field])>limit or (field=='subject' and not item[field].strip()):
                raise ValueError('任务文字为空或超过上限。')
        deps=item['blocked_by']
        if type(deps) is not list or len(deps)>20 or any(type(d) is not str or d not in tasks or d==key for d in deps) or len(set(deps))!=len(deps):
            raise ValueError('依赖必须存在、唯一且不能指向自身。')
        if item['status'] not in ('pending','in_progress','completed'):
            raise ValueError('未知任务状态。')
        if item['status']=='pending':
            if item['owner'] is not None or item['result']:
                raise ValueError('待认领任务不能已有负责人或结果。')
        else:
            identifier(item['owner'])
            if bool(item['result'].strip())!=(item['status']=='completed'):
                raise ValueError('只有完成任务需要非空结果说明。')
    for item in tasks.values():
        if item['status']!='pending' and any(tasks[d]['status']!='completed' for d in item['blocked_by']):
            raise ValueError('进行中或完成任务仍有未完成依赖。')
    def visit(key,visiting,done):
        if key in visiting:raise ValueError('依赖存在环。')
        if key in done:return
        visiting.add(key)
        for dep in tasks[key]['blocked_by']:visit(dep,visiting,done)
        visiting.remove(key);done.add(key)
    done=set()
    for key in tasks:visit(key,set(),done)
    return deepcopy(board)


def load_board(directory):
    target=Path(directory)/'tasks.json'
    try:
        with target.open('rb') as stream:raw=stream.read(64001)
    except FileNotFoundError:return {'version':1,'revision':0,'tasks':{}}
    if len(raw)>64000:raise ValueError('任务文件超过64000字节。')
    return checked_board(json.loads(raw.decode('utf-8')))


def save_board(directory,board):
    board=checked_board(board)
    payload=json.dumps(board,ensure_ascii=False,indent=2)
    if len(payload.encode('utf-8'))>64000:raise ValueError('新任务文件超过64000字节。')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,prefix='.tasks-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,directory/'tasks.json')
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def ready_ids(board):
    tasks=checked_board(board)['tasks']
    return sorted(key for key,item in tasks.items() if item['status']=='pending' and all(tasks[d]['status']=='completed' for d in item['blocked_by']))


def create_task(directory, task_id, subject, description, blocked_by):
    """依赖只能引用已存在任务；新项从pending开始，不能覆盖旧ID。"""
    task_id = identifier(task_id)
    board = load_board(directory)
    if task_id in board['tasks']:
        raise ValueError('任务ID已经存在，不覆盖。')
    item = {'id': task_id, 'subject': subject, 'description': description, 'status': 'pending',
            'owner': None, 'blocked_by': deepcopy(blocked_by), 'result': ''}
    candidate = deepcopy(board)
    candidate['tasks'][task_id] = item
    candidate['revision'] += 1
    checked_board(candidate)
    save_board(directory, candidate)
    return deepcopy(item)


def claim_task(directory, task_id, owner):
    """重新读盘，检查状态与全部依赖，再写入负责人；单写者约定。"""
    task_id, owner = identifier(task_id), identifier(owner)
    board = load_board(directory)
    if task_id not in board['tasks']:
        raise ValueError('未知任务。')
    item = board['tasks'][task_id]
    if item['status'] != 'pending':
        raise ValueError('任务已被认领或完成，不能再次认领。')
    blocked = [dep for dep in item['blocked_by'] if board['tasks'][dep]['status'] != 'completed']
    if blocked:
        raise ValueError('依赖尚未完成：' + ','.join(blocked))
    candidate = deepcopy(board)
    candidate['tasks'][task_id].update(status='in_progress', owner=owner)
    candidate['revision'] += 1
    save_board(directory, candidate)
    return deepcopy(candidate['tasks'][task_id])


def complete_task(directory, task_id, owner, result):
    """同一负责人提交结果说明；完成后重新求可开始项，不自动执行下游。"""
    task_id, owner = identifier(task_id), identifier(owner)
    board = load_board(directory)
    if task_id not in board['tasks']:
        raise ValueError('未知任务。')
    item = board['tasks'][task_id]
    if item['status'] != 'in_progress' or item['owner'] != owner:
        raise ValueError('只有进行中任务的负责人可以提交完成。')
    before = ready_ids(board)
    candidate = deepcopy(board)
    candidate['tasks'][task_id].update(status='completed', result=result)
    candidate['revision'] += 1
    checked_board(candidate)
    save_board(directory, candidate)
    unlocked = [key for key in ready_ids(candidate) if key not in before]
    return {'task': deepcopy(candidate['tasks'][task_id]), 'unlocked': unlocked}


def build_task_tools(directory,owner):
    owner=identifier(owner)
    def text(value):return json.dumps(value,ensure_ascii=False)
    return {
        'task_create':{'description':'创建pending任务，dependencies是已有任务ID的JSON数组文本；不覆盖旧ID。','parameters':{'task_id':str,'subject':str,'description':str,'dependencies':str},'run':lambda task_id,subject,description,dependencies:text(create_task(directory,task_id,subject,description,json.loads(dependencies)))},
        'task_list':{'description':'读取持久任务状态与可开始ID；不认领、不执行。','parameters':{},'run':lambda:text({'tasks':load_board(directory)['tasks'],'ready':ready_ids(load_board(directory))})},
        'task_get':{'description':'按任务ID读取完整描述与已存结果；旧结果不是本次运行证明。','parameters':{'task_id':str},'run':lambda task_id:text(get_task(directory,task_id))},
        'task_claim':{'description':'检查pending及依赖后认领；负责人由宿主绑定，不接受模型指定。','parameters':{'task_id':str},'run':lambda task_id:text(claim_task(directory,task_id,owner))},
        'task_complete':{'description':'提交当前负责人任务的完成说明，返回新解锁项，不执行下游。','parameters':{'task_id':str,'result':str},'run':lambda task_id,result:text(complete_task(directory,task_id,owner,result))},
    }


def get_task(directory,task_id):
    task_id=identifier(task_id);tasks=load_board(directory)['tasks']
    if task_id not in tasks:raise ValueError('未知任务。')
    return tasks[task_id]


def execute_task_call(call,tools,task_names,allowed=False):
    if call.get('name') in task_names:
        return _s07._s04.execute_hooked(call,tools,lambda *_:False,{},guard=lambda snapshot,registered,*_:_s07._s02.execute_tool(snapshot,registered))['result']
    return _s07.execute_with_skills(call,tools,lambda *_:allowed,{})['result']
