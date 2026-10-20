"""第二十课：在原唯一循环的边界组合机制，分别管理历史、请求与资源。"""
from copy import deepcopy
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / 's19-mcp-tools/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s20_previous', _path)
_s19 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s19)
_s07, _s10, _s11 = _s19._s07, _s19._s10, _s19._s11
run_loop = _s19.run_loop


def prepare_turn(history, compact, attach, notices):
    """压缩候选供原循环提交；记忆和通知只附在本次请求副本上。"""
    canonical = compact(deepcopy(history))
    if type(canonical) is not list or not canonical:
        raise ValueError('压缩必须返回非空历史。')
    messages = attach(deepcopy(canonical))
    if type(messages) is not list or not messages or messages[0].get('role') != 'user' or type(messages[0].get('content')) is not str:
        raise ValueError('请求必须从文本用户问题开始。')
    events = notices()
    if type(events) is not list or len(events) > 4 or any(type(x) is not str or not x.strip() or len(x) > 240 for x in events):
        raise ValueError('本轮通知最多4条，每条1到240字符。')
    if events:
        messages[0]['content'] += '\n\n[宿主通知，仅供参考]\n' + '\n'.join(events)
    if _s10._s08.history_bytes(messages) > 8000:
        raise ValueError('本次请求消息超过8000字节。')
    return {'history': canonical, 'messages': messages}


def dispatch_call(call, snapshot, ask_user, hooks):
    """一个响应只用一份能力快照；所有入口先过Hook，再走各自许可。"""
    fixed = deepcopy(call)
    def guard(current, tools, confirm, blocked=()):
        if current['name'] in snapshot['pool']['routes']:
            return _s19.call_external(current, snapshot['pool'], confirm)
        if current['name'] == 'load_skill':
            return _s07._s02.execute_tool(current, tools)
        return _s07._s04.execute_guarded(current, tools, confirm, blocked)
    handled = _s07._s04.execute_hooked(
        fixed, snapshot['builtins'], ask_user, hooks, guard=guard,
    )
    return handled


def run_session(question, capabilities, prepare, send, ask_user, hooks, close, max_calls=5):
    """只装配原run_loop；恢复只包模型，finally收尾不再发起新一轮。"""
    if type(max_calls) is not int or not 1 <= max_calls <= 8:
        raise ValueError('模型逻辑调用上限必须在1到8。')
    state = {'prepared': None, 'snapshot': None, 'warnings': []}
    recovery = {'remaining': 20, 'waited': 0.0, 'events': []}
    outcome = None
    def before(history):
        prepared = prepare(history)
        state['prepared'] = prepared
        return prepared['history']
    def ask(history):
        snapshot = freeze_capabilities(capabilities())
        state['snapshot'] = snapshot
        request = {'model': 'teaching-model', 'system': snapshot['system'],
                   'tools': deepcopy(snapshot['pool']['definitions']),
                   'messages': deepcopy(state['prepared']['messages']), 'max_tokens': 1024}
        return _s11.request_with_recovery(send, request, recovery)
    def execute(call):
        handled = dispatch_call(call, state['snapshot'], ask_user, hooks)
        state['warnings'].extend(handled['warnings'])
        return handled['result']
    try:
        outcome = run_loop(ask, execute, max_calls=max_calls, emit=lambda _: None,
                           question=question, prepare=before)
    except Exception as error:
        outcome = {'status': 'host_error', 'text': type(error).__name__, 'calls': None, 'messages': None}
    finally:
        try:
            close()
        except Exception as error:
            state['warnings'].append('收尾失败：' + type(error).__name__)
    return {'outcome': outcome, 'warnings': state['warnings'],
            'recovery': recovery}


def freeze_capabilities(current):
    """冻结定义/路由/本地元数据，保留宿主拥有的可调用接口，不复制连接。"""
    return {'system': current['system'],
            'builtins': {name: {**deepcopy({k:v for k,v in spec.items() if k != 'run'}), 'run': spec['run']}
                         for name,spec in current['builtins'].items()},
            'pool': {'definitions': deepcopy(current['pool']['definitions']),
                     'routes': {name: {**deepcopy({k:v for k,v in route.items() if k != 'invoke'}), 'invoke': route['invoke']}
                                for name,route in current['pool']['routes'].items()}}}
