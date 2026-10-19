"""第十六课：类型化请求、角色回复与按ID关闭状态。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
_path = Path(__file__).resolve().parents[2] / 's15-agent-teams/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s16_previous', _path)
_s15 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_s15)
member_name, send_message, load_inbox = _s15.member_name, _s15.send_message, _s15.load_inbox
create_team, run_teammate, prepare_inbox = _s15.create_team, _s15.run_teammate, _s15.prepare_inbox
run_loop, _s07, _s10, _s11 = _s15.run_loop, _s15._s07, _s15._s10, _s15._s11
PREFIX = '[team-protocol] '


def encode_protocol(data):
    return PREFIX + json.dumps(data, ensure_ascii=False, sort_keys=True)


def read_protocol(message):
    if type(message) is not dict or not all(type(message.get(k)) is str for k in ('sender','recipient','body')):
        raise ValueError('消息信封不符。')
    if not message['body'].startswith(PREFIX):
        return None
    data = json.loads(message['body'][len(PREFIX):])
    if type(data) is not dict or type(data.get('type')) is not str or type(data.get('request_id')) is not str:
        raise ValueError('协议类型或关联ID不符。')
    return data


def open_request(state, team, directory, sender, target, kind, payload, lock):
    """邮箱保存成功才登记pending；角色和同类未决请求先验证。"""
    member_name(sender, team); member_name(target, team)
    if kind not in ('plan', 'shutdown') or (kind == 'plan' and not (sender != 'lead' and target == 'lead')) or (kind == 'shutdown' and not (sender == 'lead' and target != 'lead')):
        raise ValueError('协议方向不符。')
    if type(payload) is not str or not 1 <= len(payload.strip()) <= 180:
        raise ValueError('请求正文需要1到180字符。')
    with lock:
        if len(state) >= 4 or any(r['status'] == 'pending' and (r['kind'], r['sender'], r['target']) == (kind, sender, target) for r in state.values()):
            raise ValueError('请求额度用完或同类请求仍未决。')
        subject = sender if kind == 'plan' else target
        if team[subject]['status'] == 'closed':
            raise ValueError('成员已经关闭。')
        request_id = 'req-' + str(len(state) + 1)
        request = {'type': kind + '_request', 'request_id': request_id, 'payload': payload.strip()}
        receipt = send_message(directory, team, sender, target, encode_protocol(request), lock)
        state[request_id] = {'kind': kind, 'sender': sender, 'target': target, 'payload': payload.strip(), 'status': 'pending', 'reply': None, 'receipt': receipt['id']}
    return {'request_id': request_id, 'status': 'pending'}


def reply_request(state, team, directory, request_id, actor, approve, feedback, lock):
    """只有目标角色能回复；忙碌成员不能确认关闭，重发不重复存信。"""
    member_name(actor, team)
    if type(approve) is not bool or type(feedback) is not str or len(feedback) > 120:
        raise ValueError('回复需要布尔决定与有界说明。')
    with lock:
        record = state.get(request_id)
        if record is None or record['target'] != actor:
            raise ValueError('没有此请求或回复身份不符。')
        response = {'type': record['kind'] + '_response', 'request_id': request_id, 'approve': approve, 'feedback': feedback}
        if record['reply'] is not None:
            if record['reply'] != response:
                raise ValueError('同一请求不能改写决定。')
            return {'request_id': request_id, 'status': 'already_sent'}
        if record['status'] != 'pending':
            raise ValueError('请求不再等待回复。')
        if record['kind'] == 'shutdown' and approve and team[actor]['active']:
            return {'request_id': request_id, 'status': 'deferred'}
        receipt = send_message(directory, team, actor, record['sender'], encode_protocol(response), lock)
        record['reply'] = response
        if record['kind'] == 'shutdown' and approve:
            team[actor]['status'] = 'closed'
    return {'request_id': request_id, 'status': 'queued', 'receipt': receipt['id']}


def match_response(state, message, recipient, lock):
    """信封角色、类型、ID和已发送决定全部一致，才更新请求状态。"""
    data = read_protocol(message)
    if data is None:
        return {'status': 'ignored', 'reason': 'ordinary_message'}
    if set(data) != {'type', 'request_id', 'approve', 'feedback'} or type(data['approve']) is not bool or type(data['feedback']) is not str or len(data['feedback']) > 120:
        return {'status': 'ignored', 'reason': 'invalid_response'}
    with lock:
        record = state.get(data['request_id'])
        if record is None or data['type'] != record['kind'] + '_response':
            return {'status': 'ignored', 'reason': 'id_or_type'}
        if recipient != record['sender'] or message['recipient'] != recipient or message['sender'] != record['target']:
            return {'status': 'ignored', 'reason': 'role_or_recipient'}
        if record['reply'] != data:
            return {'status': 'ignored', 'reason': 'not_saved_reply'}
        if record['status'] != 'pending':
            return {'request_id': data['request_id'], 'status': 'duplicate'}
        record['status'] = 'approved' if data['approve'] else 'rejected'
    return {'request_id': data['request_id'], 'status': record['status']}


def consume_responses(state, team, directory, recipient, lock):
    with lock:
        messages = load_inbox(directory, recipient, team)
    results = []
    for message in messages:
        try:
            results.append(match_response(state, message, recipient, lock))
        except (ValueError, TypeError):
            results.append({'status': 'ignored', 'reason': 'malformed_protocol'})
    return results


def plan_gate(state, request_id, actor, lock):
    """独立的协作门控；通过后仍经过原宿主权限与Hook。"""
    def before(payload):
        if payload['call']['name'] != 'run_main':
            return None
        with lock:
            record = state.get(request_id, {})
            if record.get('kind') != 'plan' or record.get('sender') != actor or record.get('status') != 'approved':
                return '本次计划尚未匹配批准回复。'
        return None
    return before
