"""第十四课：会话内时间表、触发队列与串行交付。"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import re

_path = Path(__file__).resolve().parents[2] / 's13-background-tasks/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s14_previous', _path)
_s13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s13)
_s11, _s10, _s07 = _s13._s11, _s13._s10, _s13._s07
run_loop = _s13.run_loop
LOCAL = timezone(timedelta(hours=8))


def cron_fields(expression):
    """有意限定子集：*、单值，分钟额外支持*/N；星期0为周日。"""
    if not isinstance(expression, str) or len(expression) > 80:
        raise ValueError('时间表需要有界字符串。')
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError('需要分钟、小时、日、月、星期五项。')
    limits = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    fields = []
    for index, (part, (low, high)) in enumerate(zip(parts, limits)):
        if part == '*':
            fields.append(set(range(low, high + 1)))
        elif index == 0 and re.fullmatch(r'\*/[1-9][0-9]?', part) and int(part[2:]) <= 59:
            fields.append(set(range(0, 60, int(part[2:]))))
        elif re.fullmatch(r'[0-9]{1,2}', part) and low <= int(part) <= high:
            fields.append({int(part)})
        else:
            raise ValueError('本课仅支持*、范围内单值和分钟*/1到*/59。')
    return parts, fields


def cron_matches(expression, when):
    """固定UTC+08:00解释时间；日与星期同时受限时任一满足即可。"""
    parts, fields = cron_fields(expression)
    local = checked_time(when).astimezone(LOCAL)
    minute, hour, day, month, weekday = fields
    if local.minute not in minute or local.hour not in hour or local.month not in month:
        return False
    day_ok = local.day in day
    week_ok = (local.weekday() + 1) % 7 in weekday
    if parts[2] == '*':
        return week_ok
    if parts[4] == '*':
        return day_ok
    return day_ok or week_ok


def enqueue_due(state, now, lock):
    """检查当前分钟，不补发停机期间的时刻；满队列不提前记已触发。"""
    instant = checked_time(now).astimezone(timezone.utc).replace(second=0, microsecond=0)
    slot = instant.isoformat()
    added = []
    with lock:
        for job_id, job in list(state['jobs'].items()):
            if job['last_slot'] is not None and slot <= job['last_slot']:
                continue
            if not cron_matches(job['cron'], instant) or len(state['queue']) >= 8:
                continue
            event = {'id': job_id + '@' + slot, 'job_id': job_id, 'slot': slot, 'prompt': job['prompt']}
            state['queue'].append(event)
            job['last_slot'] = slot
            if job['once']:
                del state['jobs'][job_id]
            added.append(deepcopy(event))
    return added


def dispatch_next(state, run_turn, lock, busy=False):
    """只在空闲时占用一项；锁外运行，失败记录后不自动重跑。"""
    with lock:
        if busy or state['active'] is not None:
            return {'status': 'busy'}
        if not state['queue']:
            return {'status': 'idle'}
        event = state['queue'].pop(0)
        state['active'] = event['id']
    outcome = {'id': event['id'], 'status': 'interrupted', 'text': ''}
    try:
        response = run_turn(deepcopy(event))
        outcome = {'id': event['id'], 'status': str(response['status'])[:40], 'text': str(response['text'])[:1200]}
    except Exception as error:
        outcome = {'id': event['id'], 'status': 'turn_error', 'text': type(error).__name__}
    finally:
        with lock:
            state['results'] = (state['results'] + [outcome])[-8:]
            state['active'] = None
    return deepcopy(outcome)


def checked_time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('时间必须带UTC偏移。')
    return value


def new_state():
    return {'jobs': {}, 'queue': [], 'active': None, 'results': [], 'created': 0}


def schedule_job(state, lock, expression, prompt, once=False):
    cron_fields(expression)
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 600 or type(once) is not bool:
        raise ValueError('提示需要1到600字符，once需要布尔值。')
    with lock:
        if state['created'] >= 4:
            raise ValueError('本次会话最多创建4张时间表。')
        state['created'] += 1
        job_id = 'cron-' + str(state['created'])
        state['jobs'][job_id] = {'cron': expression, 'prompt': prompt.strip(), 'once': once, 'last_slot': None}
    return job_id


def cancel_job(state, lock, job_id):
    with lock:
        removed = state['jobs'].pop(job_id, None) is not None
        state['queue'] = [event for event in state['queue'] if event['job_id'] != job_id]
    return {'cancelled': removed, 'active_cancelled': False}


def build_schedule_tools(state, lock):
    def listing():
        with lock:
            return json.dumps(deepcopy(state['jobs']), ensure_ascii=False)
    return {
        'schedule_cron': {'description': '会话内重复投递提示，不授予文件或程序权限。固定UTC+08:00；五项仅*和单值，分钟可*/N。',
                          'parameters': {'cron': str, 'prompt': str},
                          'run': lambda cron, prompt: schedule_job(state, lock, cron, prompt)},
        'list_crons': {'description': '读取本会话时间表。', 'parameters': {}, 'run': listing},
        'cancel_cron': {'description': '删除未来时间表及未交付项；不终止当前轮次。', 'parameters': {'job_id': str},
                        'run': lambda job_id: json.dumps(cancel_job(state, lock, job_id))},
    }
