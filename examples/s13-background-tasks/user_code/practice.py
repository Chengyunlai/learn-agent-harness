"""固定模型；后台main.py和独立文件读取均真实执行，无在线模型。"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import start_background, prepare_background, ProcessHandle, run_loop, _s11, _s10, _s07


def fixed_model(messages):
    turns = sum(m['role'] == 'assistant' for m in messages)
    notices = [m['content'] for m in messages if m['role'] == 'user' and isinstance(m['content'], str)
               and m['content'].startswith('[background-result] ')]
    if notices:
        event = json.loads(notices[-1].split(' ', 1)[1])
        return _s10.answer('后台结果：' + event['status'] + '；' + event['output'])
    if turns == 0:
        return _s10.use('run_background', {}, 1)
    results = [b for m in messages if isinstance(m['content'], list) for b in m['content']
               if b.get('type') == 'tool_result']
    if any(b.get('is_error') for b in results):
        return _s10.answer('没有启动后台程序：' + results[-1]['content'])
    if turns == 1:
        return _s10.use('read_file', {'path': 'expected.txt'}, 2)
    return _s10.answer('程序还在运行，交回控制权；稍后由宿主查看结果。')


def run(workspace, allowed=False, send_override=None, max_calls=4, after_read=None):
    jobs, requests, state, cache = {}, [], {'items': []}, {}
    registry = _s07.scan_skills(Path(__file__).resolve().parents[2] / 's07-skills/user_code/skills')
    tools = _s07.build_tools(workspace, state, _s10.child_model, registry)
    tools['run_background'] = {'description': '获准后在后台启动固定main.py；立即返回收据。',
                               'parameters': {}, 'run': lambda: ''}
    recovery = {'remaining': 20, 'waited': 0., 'events': []}
    def ask(history):
        system = _s10.get_system_prompt(_s10.collect_context(workspace, tools, registry, []), cache)['system']
        request = {'model': 'teaching-model', 'system': system,
                   'messages': _s07._s05.prepare_messages(history, state),
                   'tools': _s07._s05.tool_definitions(tools), 'max_tokens': 1024}
        def send(payload):
            requests.append(payload)
            return send_override(payload) if send_override else fixed_model(payload['messages'])
        return _s11.request_with_recovery(send, request, recovery, pause=lambda _: None, random_unit=lambda: 0)
    def execute(call):
        if call['name'] == 'run_background':
            # Original hook/guard chain still controls all earlier tools; this new fixed launcher has its own explicit grant.
            return _s07._s05._s04.execute_hooked(call, tools, lambda *_: allowed, {},
                guard=lambda snapshot, *_: start_background(snapshot, jobs, lambda: ProcessHandle(workspace), allowed))['result']
        result = _s07.execute_with_skills(call, tools, lambda *_: allowed, {})['result']
        if call['name'] == 'read_file' and after_read:
            after_read(jobs)
        return result
    try:
        out = run_loop(ask, execute, max_calls=max_calls,
                       question='后台运行main.py，等待时先读expected.txt；只根据真实结果报告。',
                       prepare=lambda h: prepare_background(h, jobs))
        # No model polling while idle: host waits with bounded process deadlines, then hands off the evidence.
        while any(j['result'] is None for j in jobs.values()):
            prepare_background(out['messages'], jobs)
            if any(j['result'] is None for j in jobs.values()):
                time.sleep(.01)
        final = prepare_background(out['messages'], jobs)
        return out, final, requests, jobs
    finally:
        for job in jobs.values():
            job['handle'].close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision', choices=['allow', 'deny'], default='deny')
    parser.add_argument('--workspace', type=Path, default=Path(__file__).parent / 'workspace')
    args = parser.parse_args()
    print('固定模型；真实后台进程。started不是completed；退出前回收本课直接子进程。')
    out, final, _, jobs = run(args.workspace.resolve(), args.decision == 'allow')
    print('模型停止：', out['status'], out['text'])
    for job in jobs.values():
        print('宿主最终结果：', json.dumps(job['result'], ensure_ascii=False))
    print('未交给模型的新通知：', len(final) - len(out['messages']))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
