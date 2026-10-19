"""固定模型；真实线程、只读文件与文件邮箱。队友跨两次交付保留上下文。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import create_team, send_message, prepare_inbox, run_teammate, message_tool, load_inbox, run_loop, _s07, _s10, _s11


def use(name, arguments, actor, phase, number):
    response = _s10.use(name, arguments, number)
    response['content'][0]['id'] = f'{actor}-{phase}-{number}'
    return response


def fixed_model(messages, actor):
    if actor == 'lead':
        inbox = [json.loads(m['content'].split(' ', 1)[1]) for m in messages
                 if isinstance(m['content'], str) and m['content'].startswith('[team-message] ')]
        return _s10.answer('Lead收到' + str(len(inbox)) + '条队友消息：\n' + '\n'.join(m['body'] for m in inbox) + '\n以上是只读信息，没有运行程序。')
    anchors = [i for i, m in enumerate(messages) if isinstance(m['content'], str) and m['content'].startswith('[team-turn] ')]
    anchor = anchors[-1]; phase = messages[anchor]['content'].split('\n', 1)[0].split(':')[-1]
    number = sum(m['role'] == 'assistant' for m in messages[anchor + 1:])
    if phase == '1':
        if number == 0:
            return use('read_file', {'path': 'main.py' if actor == 'reader' else 'expected.txt'}, actor, phase, 1)
        if number == 1:
            data = next(block for message in messages[anchor + 1:] if isinstance(message['content'], list)
                        for block in message['content'] if block.get('type') == 'tool_result'
                        and block.get('tool_use_id') == f'{actor}-{phase}-1')
            if data['is_error']:return _s10.answer('读取失败，不能提供文件结论。')
            return use('send_message', {'recipient': 'lead' if actor == 'reader' else 'reader',
                       'body': ('源码记录：' if actor == 'reader' else '预期记录：') + data['content']}, actor, phase, 2)
        return _s10.answer('本轮调查结束，上下文仍保留；发信收据不表示对方已经看见。')
    if number == 0:
        source = next(b['content'] for m in messages if isinstance(m['content'], list) for b in m['content']
                      if b.get('type') == 'tool_result' and b.get('tool_use_id') == 'reader-1-1')
        notices = [json.loads(m['content'].split(' ', 1)[1]) for m in messages
                   if isinstance(m['content'], str) and m['content'].startswith('[team-message] ')]
        expected = next(m['body'] for m in notices if m['sender'] == 'reviewer')
        return use('send_message', {'recipient': 'lead', 'body': '沿用上轮源码：' + source + '\n收到队友：' + expected + '\n以上只读对照，尚未运行。'}, actor, phase, 1)
    return _s10.answer('已将补充信息送到lead邮箱；本轮没有重新读取main.py。')


def run_member(previous, team, actor, phase, directory, workspace, lock, send_override=None, traces=None):
    tools = {'read_file': _s07._s02.build_tools(workspace)['read_file'],
             'send_message': message_tool(directory, team, actor, lock)}
    cache = {}; recovery = {'remaining': 20, 'waited': 0., 'events': []}
    def prepare(current):
        joined = prepare_inbox(previous + current, directory, team, actor, lock)
        return joined[len(previous):]
    def ask(current):
        history = previous + current
        system = _s10.get_system_prompt(_s10.collect_context(workspace, tools, {}, []), cache)['system']
        request = {'model': 'teaching-model', 'system': system + '\n宿主身份：' + actor + '；角色：' + team[actor]['role'],
                   'tools': _s07._s02.tool_definitions(tools), 'messages': history, 'max_tokens': 1024}
        if traces is not None:
            with lock: traces.append({'actor': actor, 'phase': phase, 'request': deepcopy(request)})
        return _s11.request_with_recovery(send_override or (lambda req: fixed_model(req['messages'], actor)), request,
                                          recovery, pause=lambda _: None, random_unit=lambda: 0)
    def execute(call):
        return _s07._s04.execute_hooked(call, tools, lambda *_: False, {},
            guard=lambda snapshot, registered, *_: _s07._s02.execute_tool(snapshot, registered))['result']
    outcome = run_loop(ask, execute, max_calls=4, emit=lambda _: None, prepare=prepare,
                       question=f'[team-turn] {actor}:{phase}\n本轮读取指定文件并交接证据；补充轮只使用已有记录。')
    outcome['messages'] = previous + outcome['messages']
    return outcome


def demo(directory, workspace, send_override=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):raise ValueError('本课从空邮箱开始，不自动恢复旧会话。')
    team, lock, traces, reports = create_team(), threading.RLock(), [], []
    def first(actor):
        result = run_teammate(team, actor, lambda history: run_member(history, team, actor, 1, directory, workspace, lock,
                               (lambda request: send_override(actor, request)) if send_override else None, traces), lock)
        with lock: reports.append(result)
    threads = [threading.Thread(target=first, args=(actor,), name='s15-' + actor) for actor in ('reader', 'reviewer')]
    try:
        for thread in threads:thread.start()
    finally:
        for thread in threads:
            if thread.ident is not None:thread.join()
    reports.append(run_teammate(team, 'reader', lambda history: run_member(history, team, 'reader', 2, directory, workspace, lock,
                   (lambda request: send_override('reader', request)) if send_override else None, traces), lock))
    lead = run_member([], team, 'lead', 1, directory, workspace, lock,
                      (lambda request: send_override('lead', request)) if send_override else None, traces)
    team['lead']['history'] = lead['messages']
    return team, reports, lead, traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).parent / 'workspace')
    parser.add_argument('--maildir', type=Path)
    args = parser.parse_args()
    def show(directory):
        team, reports, lead, traces = demo(directory, args.workspace.resolve())
        print('固定模型；真实只读文件、线程和邮箱，没有在线模型或程序执行。')
        print('队友轮次：', [(r['member'], r['status']) for r in reports])
        print(lead['text'])
        print('reader累计交付：', team['reader']['turns'], '；逻辑请求：', len(traces))
        print('邮箱保留：', {name: len(load_inbox(directory, name, team)) for name in team})
    if args.maildir:show(args.maildir)
    else:
        with tempfile.TemporaryDirectory(prefix='s15-team-') as folder:show(Path(folder))
if __name__ == '__main__':main()
