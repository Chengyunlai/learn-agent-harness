"""第十九课：外部目录变成一次模型请求的工具与路由快照。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re

_path = Path(__file__).resolve().parents[2] / 's18-worktree-isolation/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s19_previous', _path)
_previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_previous)
run_loop, _s07, _s10, _s11 = _previous.run_loop, _previous._s07, _previous._s10, _previous._s11


def checked_tool(raw):
    """只接入本课支持的必填短字符串对象；不冒充通用JSON Schema验证器。"""
    if not isinstance(raw, dict) or not isinstance(raw.get('name'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', raw.get('name', '')):
        raise ValueError('外部工具名称不受支持。')
    schema = raw.get('inputSchema')
    if not isinstance(schema, dict) or set(schema) != {'type','properties','required','additionalProperties'}:
        raise ValueError('本课只支持显式字段的字符串对象schema。')
    props = schema['properties']
    if (schema['type'] != 'object' or schema['additionalProperties'] is not False
            or not isinstance(props, dict) or len(props) > 4
            or not isinstance(schema['required'], list)
            or any(type(key) is not str for key in schema['required'])
            or len(schema['required']) != len(props) or set(schema['required']) != set(props)
            or any(not isinstance(key,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', key) or value != {'type':'string'} for key,value in props.items())):
        raise ValueError('schema超出本课支持范围。')
    if not isinstance(raw.get('description',''), str) or len(raw.get('description','')) > 400:
        raise ValueError('工具说明过长或不是文字。')
    return deepcopy(raw)


def discover_tools(list_page):
    """最多四页八项；完整验证后才返回目录，不发布半份结果。"""
    tools, seen, cursors, cursor = [], set(), set(), None
    for _ in range(4):
        page = list_page(cursor)
        if not isinstance(page, dict) or not isinstance(page.get('tools'), list):
            raise ValueError('工具目录页面不合法。')
        if len(json.dumps(page, ensure_ascii=False).encode()) > 24000:
            raise ValueError('单页目录超过24000字节。')
        for raw in page['tools']:
            tool = checked_tool(raw)
            if tool['name'] in seen or len(tools) >= 8:
                raise ValueError('工具重复或超过八项。')
            seen.add(tool['name'])
            tools.append(tool)
        cursor = page.get('nextCursor')
        if cursor is None:
            return tools
        if not isinstance(cursor, str) or not cursor or len(cursor) > 120 or cursor in cursors:
            raise ValueError('分页游标无效或重复。')
        cursors.add(cursor)
    raise ValueError('工具目录超过四页。')


def assemble_tool_pool(builtins, servers):
    """同一次组装同时产生模型定义和调用路由；失败不改旧池。"""
    definitions, routes = deepcopy(builtins), {}
    names = {item['name'] for item in definitions}
    if len(names) != len(definitions) or len(servers) > 2:
        raise ValueError('内置名称重复或服务超过两项。')
    for server, client in sorted(servers.items()):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,15}', server) or not callable(client['call']):
            raise ValueError('宿主服务名或调用接口不合法。')
        if len(client['tools']) > 8:
            raise ValueError('服务工具超过八项。')
        for raw in client['tools']:
            tool = checked_tool(raw)
            alias = 'mcp__' + server + '__' + tool['name'].replace('.', '_')
            if alias in names:
                raise ValueError('映射后的工具名冲突，保留旧池。')
            names.add(alias)
            definitions.append({'name':alias, 'description':tool.get('description',''),
                                'input_schema':deepcopy(tool['inputSchema'])})
            routes[alias] = {'server':server, 'remote':tool['name'],
                             'schema':deepcopy(tool['inputSchema']), 'invoke':client['call']}
    return {'definitions':definitions, 'routes':routes}


def result_text(reply):
    if not isinstance(reply, dict) or type(reply.get('isError',False)) is not bool:
        raise ValueError('MCP结果格式不合法。')
    blocks = reply.get('content')
    if not isinstance(blocks, list) or not blocks or len(blocks) > 4 or reply.get('structuredContent') is not None:
        raise ValueError('本课只接收一到四块纯文本结果。')
    if any(not isinstance(b,dict) or b.get('type') != 'text' or not isinstance(b.get('text'),str) for b in blocks):
        raise ValueError('结果包含本课不支持的内容类型。')
    text = '\n'.join(block['text'] for block in blocks)
    if not text.strip() or len(text) > 2000:
        raise ValueError('外部结果为空或超过2000字符。')
    return text, reply.get('isError', False)


def call_external(call, pool, ask_user):
    """宿主确认独立于server标注；一次调用，无自动工具重试。"""
    snapshot = deepcopy(call)
    envelope = {'type':'tool_result', 'tool_use_id':snapshot['id']}
    try:
        route = pool['routes'].get(snapshot.get('name'))
        if route is None:
            raise ValueError('本次工具快照中没有这个路由。')
        arguments = snapshot.get('input')
        if (not isinstance(arguments,dict) or set(arguments) != set(route['schema']['properties'])
                or any(type(value) is not str or len(value) > 120 for value in arguments.values())):
            raise ValueError('外部工具参数字段、类型或长度不符。')
        if ask_user(deepcopy(snapshot), route['server']) is not True:
            return {**envelope, 'is_error':True, 'content':'未执行：本次外部调用未获批准。'}
        reply = route['invoke'](route['remote'], deepcopy(arguments))
        text, failed = result_text(reply)
        return {**envelope, 'is_error':failed, 'content':text}
    except Exception as error:
        return {**envelope, 'is_error':True, 'content':'外部调用未能完成确认：' + type(error).__name__ + ': ' + str(error)[:180]}
