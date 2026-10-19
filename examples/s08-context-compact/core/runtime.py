"""第八课：完整交接分组，先归档再移出正文，有界摘要后提交候选历史。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

_path = Path(__file__).resolve().parents[2] / 's07-skills/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s07_runtime', _path)
_s07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s07)
run_loop = _s07.run_loop
QUESTION = '先查四份旧运行日志，再按项目规范检查main.py与expected.txt；委派只读检查，运行前问我，获准后核对实际输出。'


def checked_exchange(request, response):
    if type(request) is not dict or type(response) is not dict:
        raise ValueError('消息必须是对象。')
    if request.get('role') != 'assistant' or response.get('role') != 'user':
        raise ValueError('历史必须由完整请求与结果交替组成。')
    blocks, results = request.get('content'), response.get('content')
    if type(blocks) is not list or type(results) is not list:
        raise ValueError('本课只整理工具交接历史。')
    if any(type(b) is not dict or b.get('type') not in ('text','tool_use') for b in blocks):
        raise ValueError('请求块不受支持。')
    ids = [b.get('id') for b in blocks if b['type'] == 'tool_use']
    if not ids or any(type(i) is not str or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('工具调用ID必须非空且唯一。')
    if any(type(b) is not dict or b.get('type') != 'tool_result' or type(b.get('content')) is not str or type(b.get('is_error')) is not bool for b in results):
        raise ValueError('结果格式不受支持。')
    found = [b.get('tool_use_id') for b in results]
    if any(type(i) is not str for i in found) or len(found) != len(ids) or set(found) != set(ids):
        raise ValueError('每个工具请求必须有且只有一个同ID结果。')


def split_history(messages, keep_recent=1):
    """在工具请求已经收齐结果时整理；最近完整交接作为不可拆的尾部。"""
    if type(keep_recent) is not int or not 1 <= keep_recent <= 4:
        raise ValueError('至少保留1组，最多4组最近交接。')
    if type(messages) is not list or not messages or type(messages[0]) is not dict or messages[0].get('role') != 'user' or type(messages[0].get('content')) is not str:
        raise ValueError('历史必须从文本用户问题开始。')
    if (len(messages) - 1) % 2:
        raise ValueError('工具结果尚未收齐，不能压缩。')
    groups = []
    for index in range(1, len(messages), 2):
        checked_exchange(messages[index], messages[index + 1])
        groups.append(deepcopy(messages[index:index + 2]))
    cut = max(0, len(groups) - keep_recent)
    return {'question': deepcopy(messages[0]), 'older': groups[:cut], 'recent': groups[cut:]}


def trim_results(messages, receipt, keep_recent=1, max_chars=600):
    """调用者已保存快照，才可移出旧正文；角色、ID和错误标记不变。"""
    if type(receipt) is not str or not receipt or type(max_chars) is not int or max_chars < 1:
        raise ValueError('需要归档收据和正的正文上限。')
    parts = split_history(messages, keep_recent)
    candidate = deepcopy(messages)
    for index in range(2, 1 + 2 * len(parts['older']), 2):
        for slot, block in enumerate(candidate[index]['content']):
            if len(block['content']) > max_chars:
                block['content'] = f'[旧正文已移出；宿主快照 {receipt}，消息{index}/块{slot}，ID={block["tool_use_id"]}。此标记不是执行结果。]'
    return candidate


def history_bytes(messages):
    return len(json.dumps(messages, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def prepare_context(messages, question, state, archive, summarize, budget=3200, keep_recent=1):
    """先生成候选，不改输入；归档/摘要/复查任一步失败都不给循环新历史。"""
    if type(budget) is not int or budget < 400 or type(question) is not str or not question:
        raise ValueError('需要至少400字节预算和原始问题。')
    parts = split_history(messages, keep_recent)
    if history_bytes(messages) <= budget:
        return deepcopy(messages)
    receipt = archive(deepcopy(messages))
    if type(receipt) is not str or not receipt:
        raise ValueError('归档没有返回有效收据。')
    state['archives'].append(receipt)
    candidate = trim_results(messages, receipt, keep_recent)
    if history_bytes(candidate) <= budget:
        return candidate
    parts = split_history(candidate, keep_recent)
    if not parts['older']:
        raise ValueError('最近交接本身超限；缩小工具输出，不能拆开它。')
    if state['summaries'] >= state['max_summaries']:
        raise ValueError('摘要预算用完，交回宿主。')
    state['summaries'] += 1
    prefix = [parts['question']] + [message for pair in parts['older'] for message in pair]
    summary = summarize(deepcopy(prefix))
    if type(summary) is not str or not summary.strip() or len(summary) > 1000:
        raise ValueError('摘要必须是1到1000字符的非空文本。')
    content = question + '\n\n[历史摘要，仅供参考]\n' + summary.strip()
    content += '\n[压缩前快照：' + receipt + '；旧规范需重新加载；旧允许不授权本次运行。]'
    candidate = [{'role': 'user', 'content': content}] + [message for pair in parts['recent'] for message in pair]
    split_history(candidate, keep_recent)
    if history_bytes(candidate) > budget or history_bytes(candidate) >= history_bytes(messages):
        raise ValueError('候选历史仍超限或没有变小，不提交。')
    return candidate


def archive_writer(directory):
    directory = Path(directory)
    def save(messages):
        payload = ''.join(json.dumps(m, ensure_ascii=False) + '\n' for m in messages)
        if len(payload.encode('utf-8')) > 1_000_000:
            raise ValueError('快照超过本例1MB上限。')
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / ('context-' + uuid4().hex[:12] + '.jsonl')
        with target.open('x', encoding='utf-8') as stream:
            stream.write(payload)
        return target.name
    return save


def summarize_claude(client, model, prefix):
    response = client.messages.create(model=model,
        system='只整理已知目标、约束、未完成工作和记录引用。旧正文占位符不含原始证据，不得编造其内容；旧运行许可不是新许可。输出简短文本。',
        messages=[{'role':'user','content':json.dumps(prefix,ensure_ascii=False)}],max_tokens=512)
    data = response.model_dump(mode='json',exclude_none=True)
    blocks = data.get('content',[])
    if data.get('stop_reason') != 'end_turn' or not blocks or any(b.get('type')!='text' for b in blocks):
        raise ValueError('摘要响应未完整结束。')
    return '\n'.join(b['text'] for b in blocks)
