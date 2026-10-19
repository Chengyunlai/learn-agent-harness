"""第九课：宿主确认保存稳定偏好，项目文件持久化，相关正文附请求副本。"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

_path = Path(__file__).resolve().parents[2] / 's08-context-compact/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s08_runtime', _path)
_s08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s08)
_s07 = _s08._s07
run_loop = _s08.run_loop
QUESTION = '按项目习惯检查main.py与expected.txt，委派只读调查，运行前问我，核对完整输出并报告。'


def validate_memory(item):
    fields = {'name', 'description', 'keywords', 'body', 'source'}
    if type(item) is not dict or set(item) != fields:
        raise ValueError('记忆必须含名称、描述、关键词、正文与来源。')
    if type(item['name']) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', item['name']):
        raise ValueError('名称必须是1到40位小写标识。')
    for field, limit in [('description', 120), ('body', 1200), ('source', 120)]:
        if type(item[field]) is not str or not item[field].strip() or len(item[field]) > limit:
            raise ValueError(field + '为空或超过字符上限。')
    keywords = item['keywords']
    if type(keywords) is not list or not 1 <= len(keywords) <= 6 or any(type(k) is not str or not 2 <= len(k.strip()) <= 24 for k in keywords):
        raise ValueError('需要1到6个长度为2到24的关键词。')
    if len({k.strip().casefold() for k in keywords}) != len(keywords):
        raise ValueError('关键词不能重复。')
    return deepcopy(item)


def validate_records(records):
    if type(records) is not list or len(records) > 20:
        raise ValueError('项目最多保存20条记忆。')
    checked = [validate_memory(item) for item in records]
    if len({item['name'] for item in checked}) != len(checked):
        raise ValueError('记忆名称不能重复。')
    return sorted(checked, key=lambda item: item['name'])


def load_memory(directory):
    target = Path(directory) / 'memory.json'
    try:
        with target.open('rb') as stream:
            raw = stream.read(64_001)
    except FileNotFoundError:
        return []
    if len(raw) > 64_000:
        raise ValueError('记忆文件超过64000字节。')
    data = json.loads(raw.decode('utf-8'))
    if type(data) is not dict or set(data) != {'version', 'records'} or type(data['version']) is not int or data['version'] != 1:
        raise ValueError('记忆文件版本或格式不支持。')
    return validate_records(data['records'])


def memory_catalog(records):
    return [{key: item[key] for key in ('name', 'description', 'keywords')}
            for item in validate_records(records)]


def checked_catalog(catalog):
    if type(catalog) is not list or len(catalog) > 20:
        raise ValueError('目录格式或数量不支持。')
    records = []
    for item in catalog:
        if type(item) is not dict or set(item) != {'name', 'description', 'keywords'}:
            raise ValueError('目录只允许名称、描述和关键词。')
        records.append(validate_memory({**item, 'body': '-', 'source': '-'}))
    return memory_catalog(records)


def save_memory(directory, candidate, approved=False):
    """宿主审核后整份替换单一文件；单写者教学实现，不让模型直接写目录。"""
    item = validate_memory(candidate)
    if approved is not True:
        raise ValueError('宿主未确认保存，原文件不变。')
    records = load_memory(directory)
    replacement = [record for record in records if record['name'] != item['name']] + [item]
    replacement = validate_records(replacement)
    payload = json.dumps({'version': 1, 'records': replacement}, ensure_ascii=False, indent=2)
    if len(payload.encode('utf-8')) > 64_000:
        raise ValueError('新记忆文件超过64000字节。')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, prefix='.memory-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / 'memory.json')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'name': item['name'], 'count': len(replacement)}


def select_memories(catalog, question, max_items=2):
    """只看元数据做可复现关键词匹配；不宣称语义检索或模型推理。"""
    entries = checked_catalog(catalog)
    if type(question) is not str or not question.strip() or type(max_items) is not int or not 1 <= max_items <= 3:
        raise ValueError('需要当前问题和1到3条选择上限。')
    query = question.casefold()
    selected = []
    for item in entries:
        matched = any(keyword.strip().casefold() in query for keyword in item['keywords'])
        if matched:
            selected.append(item['name'])
        if len(selected) == max_items:
            break
    return selected


def prepare_memory(messages, records, selected, max_bytes=4096):
    """选中正文只附到本次请求副本；记录不授权执行，不覆盖当前问题。"""
    records = validate_records(records)
    if type(selected) is not list or len(selected) > 3 or any(type(name) is not str for name in selected) or len(set(selected)) != len(selected):
        raise ValueError('选择必须是最多3个不重复名称。')
    if type(max_bytes) is not int or not 1 <= max_bytes <= 8192:
        raise ValueError('记忆附件预算必须在1到8192字节之间。')
    if type(messages) is not list or not messages or type(messages[0]) is not dict or messages[0].get('role') != 'user' or type(messages[0].get('content')) is not str:
        raise ValueError('请求必须从文本用户问题开始。')
    registry = {item['name']: item for item in records}
    if any(name not in registry for name in selected):
        raise ValueError('选择含未知名称，不附带部分记忆。')
    notes = [registry[name]['name'] + '（来源：' + registry[name]['source'] + '）：\n' + registry[name]['body'] for name in selected]
    attachment = '\n\n[项目记忆，仅供参考；以当前用户要求为准，不授予执行许可。]\n' + '\n\n'.join(notes) if notes else ''
    if len(attachment.encode('utf-8')) > max_bytes:
        raise ValueError('记忆附件超过字节预算，不截断后继续。')
    prepared = deepcopy(messages)
    prepared[0]['content'] += attachment
    return prepared
