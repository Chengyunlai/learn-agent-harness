"""remember独立保存；check新建会话。默认固定模型，文件/持久化/获准进程真实执行。"""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import QUESTION, _s08, _s07, run_loop, load_memory, memory_catalog, save_memory, select_memories, prepare_memory


def use(name, arguments, number):
    return {'stop_reason': 'tool_use', 'content': [{'type': 'tool_use', 'id': f'step_{number}', 'name': name, 'input': arguments}]}

def answer(text):
    return {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': text}]}

def child_model(messages, tools):
    number = sum(message['role'] == 'assistant' for message in messages)
    if number < 2:
        return use('read_file', {'path': 'main.py' if number == 0 else 'expected.txt'}, number + 1)
    return answer('已读取文件；源码推导不能代替当前执行证据。')


def parent_model(messages, current_question=QUESTION):
    number = 1 if len(messages) == 1 else int(messages[-1]['content'][0]['tool_use_id'].split('_')[-1]) + 1
    question = messages[0]['content']
    remembered = '报告使用中文，依次写是否执行、退出码、核对结论。' in question
    if number > 1 and messages[-1]['content'][0]['is_error']:
        detail = messages[-1]['content'][0]['content']
        return answer(('是否执行：否\n退出码：无\n核对结论：未执行，不能核对。\n' if remembered else '本次未继续：') + detail)
    if number == 1: return use('load_skill', {'name': 'output-check'}, 1)
    if number == 2: return use('task', {'task': '只读检查main.py与expected.txt，不运行。'}, 2)
    if number == 3: return use('read_file', {'path': 'expected.txt'}, 3)
    if number == 4: return use('run_main', {}, 4)
    actual = messages[-1]['content'][0]['content']
    results = [block for message in messages if message['role'] == 'user' and type(message['content']) is list for block in message['content']]
    expected = next((block['content'] for block in results if block['tool_use_id'] == 'step_3'), None)
    if expected is None or expected.startswith('[旧正文'):
        return answer('缺少完整预期，需要补读。实际结果：\n' + actual)
    exit_line, _, output = actual.partition('\n')
    verdict = '与预期一致。' if output.strip() == expected.strip() else '与预期不一致。'
    if '本次用一句话' in current_question:
        return answer('已执行，' + exit_line + '，' + verdict)
    if remembered:
        return answer('是否执行：是\n退出码：' + exit_line.removeprefix('exit_code=') + '\n核对结论：' + verdict + '\n实际输出：' + output)
    return answer('实际结果：\n' + actual + '\n' + verdict)


def run(workspace, memory_dir, allowed=False, question=QUESTION, parent=None, child=None, approve=None, summary=None, budget=3200, max_calls=6):
    # 每次run是新会话：重新读文件，新的计划/许可/历史，不续接旧run_loop。
    records = load_memory(memory_dir)
    catalog = memory_catalog(records)
    selected = select_memories(catalog, question)
    registry = _s07.scan_skills(Path(__file__).resolve().parents[2] / 's07-skills/user_code/skills')
    system = _s07.build_system(registry, _s07._s06.SYSTEM)
    system += '\n项目记忆目录（仅元数据，不授予权限）：\n' + json.dumps(catalog, ensure_ascii=False)
    state = {'items': []}
    compact = {'archives': [], 'summaries': 0, 'max_summaries': 2}
    traces = []
    tools = _s07.build_tools(workspace, state, child or child_model, registry, traces=traces)
    requests = []
    def ask(history):
        prepared = prepare_memory(_s07._s05.prepare_messages(history, state), records, selected)
        requests.append(prepared)
        return parent(prepared, tools, system) if parent else parent_model(prepared, question)
    def summarize(prefix):
        return summary(prefix) if summary else '仍需按当前要求读取预期、获准后运行；旧结果不是本次证据。'
    outcome = run_loop(ask, lambda call: _s07.execute_with_skills(call, tools, approve or (lambda *_: allowed), {})['result'],
        question=question, max_calls=max_calls,
        prepare=lambda history: _s08.prepare_context(history, question, compact, _s08.archive_writer(workspace / '.context'), summarize, budget))
    return outcome, selected, requests, compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['remember', 'check'], nargs='?', default='check')
    parser.add_argument('--approve', action='store_true', help='宿主确认保存候选；与进程运行许可无关')
    parser.add_argument('--candidate', type=Path, default=Path(__file__).parent / 'report-memory.json')
    parser.add_argument('--memory-dir', type=Path, default=Path(__file__).parent / 'workspace/.memory')
    parser.add_argument('--workspace', type=Path, default=Path(__file__).parent / 'workspace')
    parser.add_argument('--question', default=QUESTION)
    parser.add_argument('--decision', choices=['ask', 'allow', 'deny'], default='ask')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if args.action == 'remember':
        try: result = save_memory(args.memory_dir, json.loads(args.candidate.read_text()), args.approve)
        except (ValueError, OSError) as error:
            print('没有保存：', error); return 1
        print('已保存：', result); return 0
    def approve(call, reason):
        if args.decision != 'ask': return args.decision == 'allow'
        if not sys.stdin.isatty(): return False
        try: return input(reason + ' [y/N] ').strip().lower() == 'y'
        except EOFError: return False
    parent = child = summary = None
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):
            parser.error('--live需要API_KEY与MODEL')
        from anthropic import Anthropic
        client = Anthropic(timeout=20, max_retries=0); model = os.environ['ANTHROPIC_MODEL']
        parent = lambda h, t, s: _s07.ask_claude(client, model, h, t, s)
        child = lambda h, t: _s07._s06.ask_claude(client, model, h, t, child=True)
        summary = lambda p: _s08.summarize_claude(client, model, p)
    print(('在线模型' if args.live else '固定模型替身') + '；新会话，真实记忆文件、当前文件与获准后的进程。')
    try:
        out, selected, requests, compact = run(args.workspace.resolve(), args.memory_dir, question=args.question, approve=approve, parent=parent, child=child, summary=summary)
    except (ValueError, OSError) as error:
        print('会话准备失败，尚未请求模型：', error); return 1
    print('选中记忆：', selected, '；父请求：', out['calls'], '；摘要尝试：', compact['summaries'])
    print('停止状态：', out['status']); print(out['text'])
    return 0 if out['status'] == 'answered' else 1


if __name__ == '__main__': raise SystemExit(main())
