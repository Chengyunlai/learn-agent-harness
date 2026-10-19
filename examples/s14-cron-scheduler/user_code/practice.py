"""默认用注入时钟演示；--serve-seconds才在本进程按真实时钟检查。"""
import argparse
from datetime import datetime
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import new_state, schedule_job, enqueue_due, dispatch_next, LOCAL, run_loop, _s07, _s10, _s11


def fixed_model(messages):
    turn = sum(m['role'] == 'assistant' for m in messages)
    if turn == 0:
        return _s10.use('read_file', {'path': 'expected.txt'}, 1)
    last = messages[-1]['content'][0]
    if last['is_error']:
        return _s10.answer('定时检查未执行：' + last['content'])
    if turn == 1:
        return _s10.use('run_main', {}, 2)
    return _s10.answer('本次程序证据：' + last['content'])


def run_check(event, workspace, allowed=False, send_override=None):
    state = {'items': []}; registry = {}; cache = {}
    tools = _s07.build_tools(workspace, state, _s10.child_model, registry)
    recovery = {'remaining': 20, 'waited': 0., 'events': []}
    def ask(history):
        system = _s10.get_system_prompt(_s10.collect_context(workspace, tools, registry, []), cache)['system']
        request = {'model': 'teaching-model', 'system': system, 'tools': _s07._s05.tool_definitions(tools),
                   'messages': _s07._s05.prepare_messages(history, state), 'max_tokens': 1024}
        return _s11.request_with_recovery(send_override or (lambda req: fixed_model(req['messages'])), request,
                                          recovery, pause=lambda _: None, random_unit=lambda: 0)
    question = '[scheduled] ' + event['id'] + '\n' + event['prompt']
    return run_loop(ask, lambda call: _s07.execute_with_skills(call, tools, lambda *_: allowed, {})['result'],
                    question=question, max_calls=3)


def demo(workspace, allowed=False):
    state, lock = new_state(), threading.RLock()
    schedule_job(state, lock, '*/5 * * * *', '读取expected.txt，获准后运行main.py，报告本次程序结果。')
    for clock in ('2026-10-19T09:00:01+08:00', '2026-10-19T09:00:40+08:00', '2026-10-19T09:05:00+08:00'):
        added = enqueue_due(state, datetime.fromisoformat(clock), lock)
        print(clock, '新增触发：', len(added), '待交付：', len(state['queue']))
    print('Agent忙时：', dispatch_next(state, lambda _: None, lock, busy=True))
    while state['queue']:
        result = dispatch_next(state, lambda event: run_check(event, workspace, allowed), lock)
        print('交付结果：', result)
    return state


def serve(workspace, allowed, seconds):
    state, lock, stop = new_state(), threading.RLock(), threading.Event()
    schedule_job(state, lock, '* * * * *', '读取expected.txt，获准后运行main.py，报告本次程序结果。')
    def producer():
        while not stop.is_set():
            enqueue_due(state, datetime.now(LOCAL), lock)
            stop.wait(.2)
    thread = threading.Thread(target=producer, name='s14-clock')
    thread.start()
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            result = dispatch_next(state, lambda event: run_check(event, workspace, allowed), lock)
            if result['status'] != 'idle': print(result)
            stop.wait(.05)
    finally:
        stop.set(); thread.join()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).parent / 'workspace')
    parser.add_argument('--decision', choices=['allow', 'deny'], default='deny')
    parser.add_argument('--serve-seconds', type=float, default=0)
    args = parser.parse_args()
    if not 0 <= args.serve_seconds <= 65: parser.error('serve-seconds需要0到65。')
    print('固定模型；真实文件与获准进程。UTC+08:00，会话内时间表；到点只入队。')
    state = serve(args.workspace.resolve(), args.decision == 'allow', args.serve_seconds) if args.serve_seconds else demo(args.workspace.resolve(), args.decision == 'allow')
    print('会话结束；未交付：', len(state['queue']), '结果：', len(state['results']))
if __name__ == '__main__': main()
