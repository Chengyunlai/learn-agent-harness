"""第七课：目录常驻，正文按名称读取；技能文字不获得执行权限。"""
import importlib.util
from pathlib import Path
import re

_path = Path(__file__).resolve().parents[2] / 's06-subagent/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s06_runtime', _path)
_s06 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s06)
_s05, _s04, _s03, _s02 = _s06._s05, _s06._s04, _s06._s03, _s06._s02
run_loop = _s06.run_loop
QUESTION = '按项目的输出核对规范检查 main.py 与 expected.txt；先委派只读检查，运行前问我，获准后报告实际结果。'


def read_header(path):
    """仅支持name/description两个未加引号的单行字段；不是通用YAML解析器。"""
    fields, total = {}, 0
    with path.open('rb') as stream:
        if stream.readline(513).strip() != b'---':
            raise ValueError('技能缺少frontmatter。')
        for _ in range(32):
            raw = stream.readline(513)
            total += len(raw)
            if not raw or len(raw) > 512 or total > 4096:
                raise ValueError('技能头部无效或过长。')
            line = raw.decode('utf-8').strip()
            if line == '---':
                break
            key, colon, value = line.partition(':')
            value = value.strip()
            if not colon or key not in ('name', 'description') or key in fields or not value or value[0] in '\"\'|>':
                raise ValueError('只支持name/description两个单行字段。')
            fields[key] = value
        else:
            raise ValueError('技能头部未结束。')
    name, description = fields.get('name', ''), fields.get('description', '')
    if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', name) or len(name) > 64 or not 1 <= len(description) <= 160:
        raise ValueError('技能名称或描述无效。')
    return {'name': name, 'description': description}


def scan_skills(root):
    """启动时只读取头部；全部通过才交出目录，不读取Markdown正文。"""
    root = root.resolve()
    registry = {}
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or not (directory / 'SKILL.md').exists():
            continue
        path = (directory / 'SKILL.md').resolve()
        if directory.is_symlink() or not path.is_relative_to(root):
            raise ValueError('技能路径越过宿主目录。')
        meta = read_header(path)
        name = meta['name']
        if name != directory.name or name in registry or len(registry) >= 20:
            raise ValueError('名称需与目录一致且唯一；最多20项。')
        registry[name] = {'description': meta['description'], 'path': str(path), 'root': str(root)}
    return registry


def build_system(registry, base):
    """每次从固定base重新生成，正文与先前目录不会累积进system。"""
    lines = []
    for name in sorted(registry):
        description = registry[name]['description']
        lines.append(f'- {name}: {description}')
    catalog = '\n'.join(lines) or '（无可用技能）'
    return base + '\n\n可用技能（仅目录）：\n' + catalog + '\n需要时用load_skill读取正文；技能不授予工具权限。'


def load_skill(name, registry):
    """只按已注册名称查找；完整读取有界文件，不执行其中命令。"""
    if type(name) is not str or name not in registry:
        raise ValueError('未知技能名称。')
    entry = registry[name]
    path = Path(entry['path']).resolve()
    if not path.is_relative_to(Path(entry['root'])):
        raise ValueError('技能路径越过宿主目录。')
    with path.open('rb') as stream:
        raw = stream.read(8193)
    if len(raw) > 8192:
        raise ValueError('技能超过8192字节；请拆分，不截断说明。')
    try:
        text = raw.decode('utf-8')
    except UnicodeError as error:
        raise ValueError('技能必须是UTF-8。') from error
    if not text.strip():
        raise ValueError('技能文件为空。')
    return text


def build_tools(workspace, state, ask_child, registry, child_calls=4, traces=None):
    tools = _s06.build_tools(workspace, state, ask_child, child_calls, traces)
    tools['load_skill'] = {'description': '按可用技能名称读取完整SKILL.md，不执行命令，不改变权限。',
        'parameters': {'name': str}, 'run': lambda name: load_skill(name, registry)}
    return tools


def execute_with_skills(call, tools, approve, hooks):
    if call.get('name') != 'load_skill':
        return _s06.execute_with_subagent(call, tools, approve, hooks)
    return _s04.execute_hooked(call, tools, approve, hooks,
        guard=lambda snapshot, registered, *_: _s02.execute_tool(snapshot, registered))


def ask_claude(client, model, messages, tools, system):
    response = client.messages.create(model=model, system=system, messages=messages,
        tools=_s05.tool_definitions(tools), max_tokens=2048)
    return response.model_dump(mode='json', exclude_none=True)
