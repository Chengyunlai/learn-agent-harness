"""第五课：有界、原子替换的内存清单；当前计划随模型请求重新提供。"""
from copy import deepcopy
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / 's04-hooks/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s04_runtime', _path)
_s04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s04)
_s03 = _s04._s03
_s02 = _s03._s02
run_loop = _s04.run_loop
QUESTION = '先读 main.py 和 expected.txt，运行之前问我；获准后运行并核对输出，报告实际结果，用清单记录进度。'
SYSTEM = '使用 todo_write 保存当前计划；每次提交完整列表。清单状态是声明，不能代替文件和程序证据。运行需要宿主许可，拒绝后如实报告。不要修改文件。'


def validate_todos(items):
    """完整校验后才返回新列表；ID唯一，最多一项进行中。"""
    if type(items) is not list or len(items) > 20:
        raise ValueError('清单必须是最多20项的列表。')
    normalized, seen, active = [], set(), 0
    for item in items:
        if type(item) is not dict or set(item) != {'id', 'content', 'status'}:
            raise ValueError('每项必须且只能包含id、content、status。')
        if any(type(item[key]) is not str for key in item):
            raise ValueError('条目字段必须是字符串。')
        key, content, status = item['id'].strip(), item['content'].strip(), item['status']
        if not key or len(key) > 32 or key in seen or not content or len(content) > 150:
            raise ValueError('ID需唯一且非空，ID最多32字符，内容1到150字符。')
        if status not in ('pending', 'in_progress', 'completed'):
            raise ValueError('未知任务状态。')
        seen.add(key)
        active += status == 'in_progress'
        if active > 1:
            raise ValueError('同时只能有一项进行中。')
        normalized.append({'id': key, 'content': content, 'status': status})
    return normalized


def format_todos(items):
    return '\n'.join(f"{item['id']} [{item['status']}] {item['content']}" for item in items) or '（清单为空）'


def write_todos(state, items):
    """一次提交整份计划；失败不改变旧状态，成功不执行清单中的动作。"""
    replacement = validate_todos(items)
    rendered = format_todos(replacement)
    state['items'] = replacement
    return rendered


def prepare_messages(messages, state):
    """只修改本次请求副本；原问题保留，当前计划不累积进原历史。"""
    prepared = deepcopy(messages)
    current = format_todos(state['items'])
    prepared[0]['content'] += '\n\n宿主提供的当前清单（状态声明，需核对证据）：\n' + current
    return prepared


def build_tools(workspace, state):
    tools = _s04.build_tools(workspace)
    tools['todo_write'] = {'description': '提交完整任务列表，更新内存计划，不执行任务。空列表清空；最多20项，同时最多一项进行中。',
        'parameters': {'items': list}, 'run': lambda items: write_todos(state, items)}
    return tools


def tool_definitions(tools):
    definitions = _s02.tool_definitions({k:v for k,v in tools.items() if k != 'todo_write'})
    definitions.append({'name':'todo_write','description':tools['todo_write']['description'],
        'input_schema':{'type':'object','properties':{'items':{'type':'array','maxItems':20,
            'items':{'type':'object','properties':{'id':{'type':'string','minLength':1,'maxLength':32},
                'content':{'type':'string','minLength':1,'maxLength':150},
                'status':{'type':'string','enum':['pending','in_progress','completed']}},
                'required':['id','content','status'],'additionalProperties':False}}},
            'required':['items'],'additionalProperties':False}})
    return definitions


def execute_with_plan(call, tools, ask_user, hooks, blocked=()):
    def authorize(snapshot, registered, approve, denied):
        # todo_write只是更新本进程计划；仍先过注册/参数检查、禁止项与before hooks。
        if snapshot.get('name') == 'todo_write' and 'todo_write' not in denied:
            return _s02.execute_tool(snapshot, registered)
        return _s03.execute_guarded(snapshot, registered, approve, denied)
    return _s04.execute_hooked(call, tools, ask_user, hooks, blocked, guard=authorize)


def ask_claude(client, model, messages, tools):
    response = client.messages.create(model=model, system=SYSTEM, messages=messages,
        tools=tool_definitions(tools), max_tokens=2048)
    return response.model_dump(mode='json', exclude_none=True)
