"""固定模型，真实Git/双线程/文件及获准的Python进程；不调用在线模型。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from threading import Barrier, RLock, Thread
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import *
from runtime import _s07, _s10, _s11

VARIANTS = {'alpha': 'print(6 * 7)\n', 'beta': 'print(40 + 3)\n'}


def seed(root):
    repo = root / 'repo'; repo.mkdir()
    git(repo, 'init', '-b', 'main')
    (repo / 'main.py').write_text('print(0)\n')
    git(repo, 'add', 'main.py')
    git(repo, '-c', 'user.name=Teaching Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture base')
    return repo


def fixed_model(messages, actor):
    replies = sum(m['role'] == 'assistant' for m in messages)
    if replies < 2:
        answer = _s10.use('write_variant' if replies == 0 else 'run_main', {}, replies + 1)
        answer['content'][0]['id'] = f'{actor}-{replies + 1}'
        return answer
    return _s10.answer('如实报告工具反馈，不声称已合并。')


def demo(root, allowed=False, send_override=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()): raise ValueError('需要空实验目录；不自动恢复旧会话。')
    repo = seed(root); parent, directory = root / 'worktrees', root / 'board'
    bindings, team, lock, reports, traces = {}, create_team(), RLock(), {}, []
    for task_id in VARIANTS:
        create_task(directory, task_id, '独立修改并检查main.py', '固定版本，不开放任意脚本。', [])
        create_workspace(repo, parent, directory, bindings, task_id, lock)
    rendezvous = Barrier(2, timeout=10)

    def worker(actor):
        picked = claim_next(directory, team, actor, lock)
        task_id = picked['task']['id']; box = {}
        path = Path(workspace_for_task(repo, parent, directory, bindings, task_id, actor, lock))
        try:
            rendezvous.wait()  # 两个成员先各持目录，再开始工具工作。
            def turn(previous):
                tools = _s07._s02.build_tools(path)
                tools.pop('read_file')
                def write():
                    target = path / 'main.py'
                    if target.is_symlink(): raise ValueError('固定文件不能是符号链接。')
                    target.write_text(VARIANTS[task_id]); return 'written ' + task_id
                tools['write_variant'] = {'description': '将宿主登记的固定版本写入本任务main.py。', 'parameters': {}, 'run': write}
                cache, recovery = {}, {'remaining': 20, 'waited': 0.0, 'events': []}
                def ask(messages):
                    request = {'model': 'teaching-model', 'system': _s10.get_system_prompt(_s10.collect_context(path, tools, {}, []), cache)['system'], 'tools': _s07._s02.tool_definitions(tools), 'messages': messages, 'max_tokens': 1024}
                    with lock: traces.append({'actor': actor, 'request': deepcopy(request)})
                    return _s11.request_with_recovery(send_override or (lambda req: fixed_model(req['messages'], actor)), request, recovery, pause=lambda _: None, random_unit=lambda: 0)
                def guard(call, registered, ask_user, blocked=()):
                    if call['name'] != 'write_variant': return _s07._s04.execute_guarded(call, registered, ask_user, blocked)
                    error = _s07._s02.validate_call(call, registered)
                    if error or ask_user(deepcopy(call), '写入本任务固定版本') is not True:
                        return {'type': 'tool_result', 'tool_use_id': call['id'], 'is_error': True, 'content': error or '未执行：写入未获批准。'}
                    return _s07._s02.execute_tool(call, registered)
                def owner_check(payload):
                    with lock:
                        task = load_board(directory)['tasks'][task_id]
                        checked_workspace(repo, parent, bindings[task_id], task_id)
                        if task['owner'] != actor or task['status'] != 'in_progress': return '负责人已改变。'
                    return None
                def execute(call):
                    return _s07._s04.execute_hooked(call, tools, lambda *_: allowed, {'before': [owner_check]}, guard=guard)['result']
                result = run_loop(ask, execute, max_calls=4, emit=lambda _: None, question=f'{actor}:只在本任务目录写固定版本、运行并报告。')
                box['outcome'] = result
                return result
            receipt = run_teammate(team, actor, turn, lock)
            outcome = box.get('outcome', receipt)
            results = [b for m in outcome.get('messages', []) if isinstance(m['content'], list) for b in m['content'] if b.get('type') == 'tool_result']
            expected = '42' if task_id == 'alpha' else '43'
            success = outcome['status'] == 'answered' and len(results) == 2 and all(not b['is_error'] for b in results) and results[-1]['content'].strip() == 'exit_code=0\n' + expected and (path / 'main.py').read_text() == VARIANTS[task_id]
            with lock:
                if success: complete_task(directory, task_id, actor, results[-1]['content'])
                reports[task_id] = {'actor': actor, 'status': 'completed' if success else 'needs_attention', 'output': results[-1]['content'] if results else '', 'cwd': str(path)}
        except Exception as error:
            with lock: reports[task_id] = {'status': 'failed', 'error': type(error).__name__ + ': ' + str(error)}
        finally:
            with lock: bindings[task_id]['active'] = False
    threads = [Thread(target=worker, args=(actor,)) for actor in ('reader', 'reviewer')]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    cleanup = {task_id: retire_workspace(repo, parent, bindings, task_id, 'remove', lock) for task_id in VARIANTS}
    for task_id in VARIANTS:
        if cleanup[task_id]['status'] == 'needs_review': retire_workspace(repo, parent, bindings, task_id, 'keep', lock)
    return {'reports': reports, 'cleanup': cleanup, 'bindings': bindings, 'board': load_board(directory), 'main': (repo / 'main.py').read_text(), 'traces': traces}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision', choices=['allow', 'deny'], default='deny')
    parser.add_argument('--state-dir', type=Path, help='保留真实实验目录供检查；必须为空。')
    args = parser.parse_args()
    def show(root):
        result = demo(root, args.decision == 'allow')
        print('固定模型；真实Git、双线程与获准进程；没有在线模型。')
        print(json.dumps({k: v for k,v in result.items() if k != 'traces'}, ensure_ascii=False, indent=2))
        print('逻辑请求：', len(result['traces']))
    if args.state_dir: show(args.state_dir)
    else:
        with tempfile.TemporaryDirectory(prefix='s18-worktree-') as folder: show(folder)

if __name__ == '__main__': main()
