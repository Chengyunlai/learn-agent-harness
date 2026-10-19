"""默认固定主/子模型，真实文件与获准进程；只读模式实际移除run_main。"""
import argparse
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import importlib.util
_core_path = Path(__file__).resolve().parents[1] / 'core/runtime.py'
_core_spec = importlib.util.spec_from_file_location('s10_core', _core_path)
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)
QUESTION, _s09, _s08, _s07 = _core.QUESTION, _core._s09, _core._s08, _core._s07
run_loop, collect_context, get_system_prompt = _core.run_loop, _core.collect_context, _core.get_system_prompt


def use(name, arguments, number):
    return {'stop_reason': 'tool_use', 'content': [{'type': 'tool_use', 'id': f'step_{number}', 'name': name, 'input': arguments}]}


def answer(text):
    return {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': text}]}


def child_model(messages, tools):
    number = sum(message['role'] == 'assistant' for message in messages)
    if number < 2: return use('read_file', {'path': 'main.py' if number == 0 else 'expected.txt'}, number + 1)
    return answer('已调查当前文件；只读推导不等于已经执行。')


def parent_model(messages, tools, system):
    steps = []
    if 'load_skill' in tools: steps.append(('load_skill', {'name': 'output-check'}))
    if 'task' in tools: steps.append(('task', {'task': '只读调查main.py与expected.txt，不运行。'}))
    steps.append(('read_file', {'path': 'expected.txt'}))
    if 'run_main' in tools: steps.append(('run_main', {}))
    number = 1 if len(messages) == 1 else int(messages[-1]['content'][0]['tool_use_id'].split('_')[-1]) + 1
    if number > 1 and messages[-1]['content'][0]['is_error']:
        return answer('核对结论：未执行，不能核对。\n' + messages[-1]['content'][0]['content'])
    if number <= len(steps): return use(*steps[number - 1], number)
    if 'run_main' not in tools: return answer('核对结论：未运行，不能确认实际输出一致。\n本次没有注册run_main，只完成文件调查。')
    results = [block for message in messages if message['role'] == 'user' and type(message['content']) is list for block in message['content']]
    expected_id = 'step_' + str(next(i + 1 for i, step in enumerate(steps) if step[0] == 'read_file'))
    expected = next((block['content'] for block in results if block['tool_use_id'] == expected_id), None)
    actual = messages[-1]['content'][0]['content']
    if expected is None or expected.startswith('[旧正文'): return answer('缺少完整预期，不能核对。\n' + actual)
    exit_line, _, output = actual.partition('\n')
    verdict = '与预期一致。' if output.strip() == expected.strip() else '与预期不一致。'
    return answer('核对结论：' + verdict + '\n是否执行：是\n退出码：' + exit_line.removeprefix('exit_code=') + '\n实际输出：' + output)


def run(workspace, memory_dir=None, readonly=False, skills_enabled=True, allowed=False, parent=None, child=None, approve=None, summary=None, question=QUESTION, max_calls=6):
    records = _s09.load_memory(memory_dir) if memory_dir is not None else []
    selected = _s09.select_memories(_s09.memory_catalog(records), question)
    registry = _s07.scan_skills(Path(__file__).resolve().parents[2] / 's07-skills/user_code/skills') if skills_enabled else {}
    state = {'items': []}; traces = []; cache = {}; prompts = []
    compact = {'archives': [], 'summaries': 0, 'max_summaries': 2}
    tools = _s07.build_tools(workspace, state, child or child_model, registry, traces=traces)
    if readonly: tools.pop('run_main')
    if not skills_enabled: tools.pop('load_skill')
    # 装配失败在第一次模型请求之前暴露；之后每次请求仍重新取得实际状态。
    collect_context(workspace, tools, registry, records)
    def ask(history):
        context = collect_context(workspace, tools, registry, records)
        prompt = get_system_prompt(context, cache); prompts.append(prompt)
        prepared = _s09.prepare_memory(_s07._s05.prepare_messages(history, state), records, selected)
        return (parent or parent_model)(prepared, tools, prompt['system'])
    out = run_loop(ask, lambda call: _s07.execute_with_skills(call, tools, approve or (lambda *_: allowed), {})['result'],
        question=question, max_calls=max_calls,
        prepare=lambda history: _s08.prepare_context(history, question, compact, _s08.archive_writer(workspace / '.context'), summary or (lambda _: '继续按当前问题取得本次许可与执行证据。')))
    return out, prompts, tools, compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read-only', action='store_true')
    parser.add_argument('--no-skills', action='store_true')
    parser.add_argument('--memory-dir', type=Path)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).parent / 'workspace')
    parser.add_argument('--decision', choices=['ask', 'allow', 'deny'], default='ask')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    def approve(call, reason):
        if args.decision != 'ask': return args.decision == 'allow'
        if not sys.stdin.isatty(): return False
        try: return input(reason + ' [y/N] ').strip().lower() == 'y'
        except EOFError: return False
    parent = child = summary = None
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'): parser.error('--live需要API_KEY与MODEL')
        from anthropic import Anthropic
        client = Anthropic(timeout=20, max_retries=0); model = os.environ['ANTHROPIC_MODEL']
        parent = lambda h,t,s: _s07.ask_claude(client, model, h, t, s)
        child = lambda h,t: _s07._s06.ask_claude(client, model, h, t, child=True)
        summary = lambda p: _s08.summarize_claude(client, model, p)
    print(('在线模型' if args.live else '固定主/子模型替身') + '；真实注册、文件与获准进程，本地复用不是API缓存。')
    try: out, prompts, tools, compact = run(args.workspace.resolve(), args.memory_dir, args.read_only, not args.no_skills, parent=parent, child=child, approve=approve, summary=summary)
    except (ValueError, OSError) as error:
        print('请求准备失败：', error); return 1
    if prompts:
        print('system段落：', prompts[-1]['section_ids'])
        print('本地复用：', [item['reused'] for item in prompts])
    print('父模型请求：', out['calls'], '；摘要尝试：', compact['summaries'])
    print('停止状态：', out['status']); print(out['text'])
    return 0 if out['status'] == 'answered' else 1


if __name__ == '__main__': raise SystemExit(main())
