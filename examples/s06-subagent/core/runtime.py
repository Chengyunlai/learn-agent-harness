"""第六课：独立消息、只读工具、有界运行、只返回结论的同步子任务。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / 's05-todo-write/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s05_runtime', _path)
_s05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s05)
_s04, _s03, _s02 = _s05._s04, _s05._s03, _s05._s02
run_loop = _s05.run_loop
QUESTION = '请先委派只读助手检查 main.py 和 expected.txt，说明预期；然后问我是否允许运行，核对实际结果。'
SYSTEM = '用 task 委派只读检查。子任务结论只是参考，运行仍要宿主许可；用 todo_write 记录计划，如实报告未执行或失败。'
CHILD_SYSTEM = '只读检查 main.py 与 expected.txt，说明源码推导的输出和预期是否一致。禁止声称已运行；遇到证据不足明确说明。'


def child_tools(tools):
    """宿主白名单生成独立注册表；不继承运行、清单和再次委派能力。"""
    selected = {}
    for name in ('read_file',):
        if name not in tools:
            raise ValueError('缺少只读工具：' + name)
        selected[name] = deepcopy(tools[name])
    return selected


def run_subagent(task, tools, ask, max_calls=4, emit=print):
    """每次调用创建新历史；同步等待，复用原循环的停止与协议判断。"""
    if type(task) is not str or not task.strip() or len(task) > 600:
        raise ValueError('子任务必须是1到600字符的文本。')
    if type(max_calls) is not int or not 1 <= max_calls <= 8:
        raise ValueError('子循环预算必须是1到8次模型请求。')
    restricted = child_tools(tools)
    entries, warnings = [], []
    def execute(call):
        hooks = {'before': [lambda p: _s04.audit_event('before', p, entries)],
                 'after': [lambda p: _s04.audit_event('after', p, entries)]}
        report = _s04.execute_hooked(call, restricted, lambda *_: False, hooks)
        warnings.extend(report['warnings'])
        return report['result']
    outcome = run_loop(lambda history: ask(history, restricted), execute,
                       max_calls=max_calls, emit=emit, question=task.strip())
    return outcome


def task_result(call, outcome):
    """父循环只获得关联ID、停止状态和有界结论；子历史保留在宿主。"""
    status = outcome['status']
    text = outcome['text']
    failed = status != 'answered'
    if len(text) > 1200:
        text = text[:1200] + '（结论过长，已截断；请缩小子任务）'
        failed = True
    payload = {'status': status, 'summary': text, 'calls': outcome['calls']}
    return {'type': 'tool_result', 'tool_use_id': call['id'],
            'content': json.dumps(payload, ensure_ascii=False), 'is_error': failed}


def build_tools(workspace, state, ask_child, child_calls=4, traces=None):
    tools = _s05.build_tools(workspace, state)
    def delegate(task):
        outcome = run_subagent(task, tools, ask_child, child_calls)
        if traces is not None:
            traces.append(deepcopy(outcome))
        # The dispatcher preserves the original request ID outside this callable.
        return outcome
    tools['task'] = {'description': '委派只读文件检查；独立消息，只返回结论，不能运行或再次委派。',
        'parameters': {'task': str}, 'run': delegate}
    return tools


def execute_with_subagent(call, tools, approve, hooks):
    def guard(snapshot, registered, ask_user, blocked):
        if snapshot.get('name') == 'task':
            error = _s02.validate_call(snapshot, registered)
            if error:
                return {'type':'tool_result','tool_use_id':snapshot['id'],'content':error,'is_error':True}
            try:
                outcome = registered['task']['run'](**snapshot['input'])
                return task_result(snapshot, outcome)
            except ValueError as error:
                return {'type':'tool_result','tool_use_id':snapshot['id'],'content':str(error),'is_error':True}
        if snapshot.get('name') == 'todo_write':
            return _s02.execute_tool(snapshot, registered)
        return _s03.execute_guarded(snapshot, registered, ask_user, blocked)
    return _s04.execute_hooked(call, tools, approve, hooks, guard=guard)


def ask_claude(client, model, messages, tools, child=False):
    response = client.messages.create(model=model, system=CHILD_SYSTEM if child else SYSTEM,
        messages=messages, tools=(_s02.tool_definitions(tools) if child else _s05.tool_definitions(tools)), max_tokens=2048)
    return response.model_dump(mode='json', exclude_none=True)
