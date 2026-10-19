"""第十五课：独立队友上下文与追加式文件邮箱。"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

_path = Path(__file__).resolve().parents[2] / 's14-cron-scheduler/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s15_previous', _path)
_s14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s14)
_s11, _s10, _s07 = _s14._s11, _s14._s10, _s14._s07
run_loop = _s14.run_loop


def member_name(name, members):
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,23}', name) or name not in members:
        raise ValueError('只能使用已登记的成员名。')
    return name


def load_inbox(directory, recipient, members):
    member_name(recipient, members)
    target = Path(directory) / (recipient + '.jsonl')
    if target.is_symlink():
        raise ValueError('邮箱不能是符号链接。')
    if not target.exists():
        return []
    with target.open('rb') as stream:
        data = stream.read(32001)
    if len(data) > 32000:
        raise ValueError('邮箱文件超过限制。')
    items = [json.loads(line) for line in data.decode('utf-8').splitlines()]
    if len(items) > 8:
        raise ValueError('单个邮箱最多8条消息。')
    for index, item in enumerate(items, 1):
        if type(item) is not dict or set(item) != {'id', 'sender', 'recipient', 'body'}:
            raise ValueError('邮箱记录字段不符。')
        if item['id'] != recipient + '-' + str(index) or item['recipient'] != recipient:
            raise ValueError('邮箱序号或收件人不符。')
        member_name(item['sender'], members)
        if type(item['body']) is not str or not 1 <= len(item['body']) <= 600:
            raise ValueError('消息正文长度不符。')
    return items


def save_inbox(directory, recipient, items):
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    payload = ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in items)
    if len(payload.encode('utf-8')) > 32000:
        raise ValueError('邮箱文件超过限制。')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=root, delete=False) as stream:
            temporary = stream.name
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, root / (recipient + '.jsonl'))
    finally:
        if temporary is not None and Path(temporary).exists():
            Path(temporary).unlink()


def send_message(directory, members, sender, recipient, body, lock):
    """先保存到对方邮箱；queued不代表接收方模型已经读取。"""
    member_name(sender, members)
    member_name(recipient, members)
    if not isinstance(body, str) or not 1 <= len(body.strip()) <= 600:
        raise ValueError('正文需要1到600字符。')
    with lock:
        items = load_inbox(directory, recipient, members)
        if len(items) >= 8:
            raise ValueError('邮箱已满，不覆盖旧消息。')
        message = {'id': recipient + '-' + str(len(items) + 1), 'sender': sender,
                   'recipient': recipient, 'body': body.strip()}
        save_inbox(directory, recipient, items + [message])
    return {'id': message['id'], 'status': 'queued'}


def prepare_inbox(history, directory, members, recipient, lock):
    """读消息不删除；以已经提交的历史去重，丢弃候选不会丢信。"""
    with lock:
        items = load_inbox(directory, recipient, members)
    candidate = deepcopy(history)
    for message in items:
        text = '[team-message] ' + json.dumps(message, ensure_ascii=False, sort_keys=True)
        present = any(item.get('role') == 'user' and item.get('content') == text for item in candidate)
        if not present:
            candidate.append({'role': 'user', 'content': text})
    if len(candidate) > 80:
        raise ValueError('队友历史超过80条，交回宿主检查。')
    return candidate


def run_teammate(team, name, run_turn, lock):
    """同一队友复用历史；锁外运行，正常回答后仍可接一次追问。"""
    member_name(name, team)
    with lock:
        member = team[name]
        if name == 'lead' or member['active'] or member['status'] != 'idle' or member['turns'] >= 2:
            return {'member': name, 'status': 'unavailable'}
        history = deepcopy(member['history'])
        member.update(active=True, status='running', turns=member['turns'] + 1)
    try:
        outcome = run_turn(history)
        if (type(outcome) is not dict or type(outcome.get('messages')) is not list
                or len(outcome['messages']) > 80 or type(outcome.get('status')) is not str
                or type(outcome.get('text')) is not str):
            raise ValueError('轮次没有交回有界历史。')
        with lock:
            member['history'] = deepcopy(outcome['messages'])
            member['status'] = 'idle' if outcome['status'] == 'answered' else 'stopped'
        return {'member': name, 'status': outcome['status'], 'text': str(outcome['text'])[:600]}
    except Exception as error:
        with lock:
            member['status'] = 'failed'
        return {'member': name, 'status': 'failed', 'text': type(error).__name__}
    finally:
        with lock:
            member['active'] = False
            if member['status'] == 'running':
                member['status'] = 'stopped'


def create_team():
    return {name: {'role': role, 'history': [], 'active': False, 'status': 'idle', 'turns': 0}
            for name, role in [('lead', '汇总只读证据'), ('reader', '读取源码并保留调查上下文'),
                               ('reviewer', '读取预期并通知reader')]}


def message_tool(directory, members, sender, lock):
    member_name(sender, members)
    return {'description': '向已登记成员的邮箱保存一条短消息，不改变对方权限或任务状态。',
            'parameters': {'recipient': str, 'body': str},
            'run': lambda recipient, body: json.dumps(send_message(directory, members, sender, recipient, body, lock))}
