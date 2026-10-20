"""第十八课：任务绑定独立 Git 工作树；工具显式 cwd，不切进程全局目录。"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import re
import subprocess

_path = Path(__file__).resolve().parents[2] / 's17-autonomous-agents/core/runtime.py'
_spec = importlib.util.spec_from_file_location('s18_previous', _path)
_previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_previous)
load_board, create_task, complete_task = _previous.load_board, _previous.create_task, _previous.complete_task
claim_next, create_team, run_teammate = _previous.claim_next, _previous.create_team, _previous.run_teammate
run_loop, _s07, _s10, _s11 = _previous.run_loop, _previous._s07, _previous._s10, _previous._s11


def git(repo, *args):
    """固定参数列表，无shell；教学仓库由宿主创建，不运行不受信任的仓库。"""
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError('Git失败：' + result.stderr.strip()[:600])
    return result.stdout.strip()


def workspace_target(repo, parent, task_id):
    if not isinstance(task_id, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', task_id):
        raise ValueError('任务ID仅接受小写字母、数字和短横线。')
    repo, parent = Path(repo).resolve(), Path(parent).resolve()
    if parent == repo or parent.is_relative_to(repo):
        raise ValueError('工作树容器必须在主目录外。')
    path = parent / task_id
    if path.is_symlink() or path.resolve().parent != parent:
        raise ValueError('工作树路径不允许符号链接。')
    return path, 'codex/' + task_id


def checked_workspace(repo, parent, record, task_id):
    path, branch = workspace_target(repo, parent, task_id)
    if record['path'] != str(path) or record['branch'] != branch or record['status'] == 'removed':
        raise ValueError('绑定路径或生命周期不符。')
    if git(path, 'rev-parse', '--show-toplevel') != str(path):
        raise ValueError('目录不再是登记的工作树。')
    common = lambda cwd: (Path(cwd) / git(cwd, 'rev-parse', '--git-common-dir')).resolve()
    if common(path) != common(repo) or git(path, 'branch', '--show-current') != branch:
        raise ValueError('仓库归属或当前分支已改变。')
    return path


def create_workspace(repo, parent, directory, bindings, task_id, lock):
    """先创建真实工作树，再登记绑定；不认领、不完成任务。"""
    with lock:
        path, branch = workspace_target(repo, parent, task_id)
        task = load_board(directory)['tasks'][task_id]
        if task['status'] != 'pending' or task['owner'] is not None:
            raise ValueError('只为尚未认领的任务准备目录。')
        if task_id in bindings or len(bindings) >= 4:
            raise ValueError('已有绑定或达到四项目录额度。')
        base = git(repo, 'rev-parse', 'HEAD')
        git(repo, 'worktree', 'add', '-b', branch, str(path), base)
        record = {'path': str(path), 'branch': branch, 'base': base,
                  'status': 'ready', 'active': False}
        bindings[task_id] = record
    return deepcopy(record)


def workspace_for_task(repo, parent, directory, bindings, task_id, actor, lock):
    """核对最新owner，预留目录给这一轮；工具在锁外用返回路径。"""
    with lock:
        task = load_board(directory)['tasks'][task_id]
        if task['status'] != 'in_progress' or task['owner'] != actor:
            raise ValueError('当前成员没有持有这项任务。')
        record = bindings[task_id]
        if record['active']:
            raise ValueError('这项目录已经有活跃轮次。')
        path = checked_workspace(repo, parent, record, task_id)
        record['active'] = True
    return str(path)


def retire_workspace(repo, parent, bindings, task_id, action, lock):
    """先停工作再收尾；默认保留，清理不强删、不删分支、不改任务。"""
    if action not in ('keep', 'remove'):
        raise ValueError('收尾动作只接受keep或remove。')
    with lock:
        record = bindings[task_id]
        path = checked_workspace(repo, parent, record, task_id)
        if record['active']:
            return {'status': 'busy'}
        if action == 'keep':
            record['status'] = 'kept'
            return {'status': 'kept', 'branch': record['branch'], 'path': str(path)}
        dirty = git(path, 'status', '--porcelain', '--untracked-files=all', '--ignored=matching')
        head = git(path, 'rev-parse', 'HEAD')
        if dirty or head != record['base']:
            return {'status': 'needs_review', 'dirty': bool(dirty), 'changed_head': head != record['base']}
        git(repo, 'worktree', 'remove', str(path))
        record['status'] = 'removed'
    return {'status': 'removed', 'branch': record['branch']}
