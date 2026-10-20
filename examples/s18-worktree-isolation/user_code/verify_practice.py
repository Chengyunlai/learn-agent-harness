"""真实临时Git仓库验证；不会在本公开仓库创建或删除工作树。"""
import tempfile
from pathlib import Path
from threading import RLock, Thread, Barrier
import unittest
from unittest.mock import patch
from practice import demo,seed,VARIANTS
import runtime as core

class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='s18-test-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=seed(self.root);self.parent=self.root/'trees';self.board=self.root/'board';self.bindings={};self.lock=RLock()
        core.create_task(self.board,'alpha','修改','固定',[])
    def create(self):return core.create_workspace(self.repo,self.parent,self.board,self.bindings,'alpha',self.lock)
    def retire(self):return core.retire_workspace(self.repo,self.parent,self.bindings,'alpha','remove',self.lock)
    def test_two_real_directories(self):
        out=demo(self.root/'demo',True)
        self.assertEqual(out['main'],'print(0)\n');self.assertEqual(len(out['traces']),6)
        self.assertEqual({r['actor'] for r in out['reports'].values()},{'reader','reviewer'})
        for key,source in VARIANTS.items():
            self.assertEqual((Path(out['bindings'][key]['path'])/'main.py').read_text(),source)
            self.assertEqual(out['reports'][key]['status'],'completed');self.assertEqual(out['cleanup'][key]['status'],'needs_review')
    def test_denied(self):
        out=demo(self.root/'demo');self.assertTrue(all(t['status']=='in_progress' for t in out['board']['tasks'].values()))
        self.assertTrue(all(x['status']=='removed' for x in out['cleanup'].values()))
    def test_bind_does_not_claim_or_copy_dirty(self):
        (self.repo/'main.py').write_text('print(99)\n');(self.repo/'local').write_text('not committed')
        record=self.create();path=Path(record['path'])
        self.assertEqual((path/'main.py').read_text(),'print(0)\n');self.assertFalse((path/'local').exists())
        self.assertEqual(core.load_board(self.board)['tasks']['alpha']['status'],'pending')
    def test_concurrent_create_unique(self):
        barrier=Barrier(2);out=[]
        def run():
            barrier.wait()
            try:out.append(self.create()['status'])
            except ValueError:out.append('rejected')
        threads=[Thread(target=run) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertCountEqual(out,['ready','rejected'])
    def test_owner_and_active(self):
        self.create();core._previous.claim_task(self.board,'alpha','reader')
        with self.assertRaises(ValueError):core.workspace_for_task(self.repo,self.parent,self.board,self.bindings,'alpha','reviewer',self.lock)
        path=core.workspace_for_task(self.repo,self.parent,self.board,self.bindings,'alpha','reader',self.lock)
        self.assertEqual(self.retire()['status'],'busy');self.assertTrue(Path(path).exists())
    def test_dirty_untracked_ignored(self):
        path=Path(self.create()['path'])
        for filename,content in [('main.py','changed'),('extra','untracked')]:
            (path/filename).write_text(content)
            self.assertTrue(self.retire()['dirty'])
            if filename=='main.py':core.git(path,'restore','main.py')
            else:(path/filename).unlink()
        exclude=Path(core.git(path,'rev-parse','--git-path','info/exclude'))
        if not exclude.is_absolute():exclude=path/exclude
        exclude.write_text('cache\n');(path/'cache').write_text('ignored only')
        self.assertEqual(core.git(path,'status','--porcelain'),'')
        self.assertTrue(self.retire()['dirty']);self.assertTrue(path.exists())
    def test_later_merge_can_conflict(self):
        out=demo(self.root/'demo',True)
        for key in VARIANTS:
            path=out['bindings'][key]['path'];core.git(path,'add','main.py')
            core.git(path,'-c','user.name=Teaching Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m',key)
        repo=self.root/'demo/repo';core.git(repo,'merge','--ff-only','codex/alpha')
        with self.assertRaises(ValueError):core.git(repo,'-c','user.name=Teaching Fixture','-c','user.email=fixture@example.invalid','merge','--no-commit','--no-ff','codex/beta')
        self.assertIn('UU main.py',core.git(repo,'status','--porcelain'))
        core.git(repo,'merge','--abort')
    def test_committed_result_preserved(self):
        path=Path(self.create()['path']);(path/'main.py').write_text('print(42)\n');core.git(path,'add','main.py')
        core.git(path,'-c','user.name=Teaching Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','variant')
        self.assertEqual(core.git(path,'status','--porcelain'),'');out=self.retire();self.assertTrue(out['changed_head']);self.assertTrue(path.exists())
    def test_clean_remove_keeps_branch_and_task(self):
        record=self.create();before=core.load_board(self.board);self.assertEqual(self.retire()['status'],'removed')
        self.assertFalse(Path(record['path']).exists());self.assertEqual(core.git(self.repo,'rev-parse',record['branch']),record['base']);self.assertEqual(core.load_board(self.board),before)
    def test_wrong_branch_rejected(self):
        path=self.create()['path'];core.git(path,'switch','-c','other')
        with self.assertRaises(ValueError):self.retire()
    def test_invalid_path_symlink(self):
        for key in ['../x','-alpha','A','x/y','x'*33]:
            with self.assertRaises(ValueError):core.workspace_target(self.repo,self.parent,key)
        self.parent.mkdir();(self.parent/'alpha').symlink_to(self.repo,target_is_directory=True)
        with self.assertRaises(ValueError):self.create()
    def test_git_failure_no_false_binding(self):
        core.git(self.repo,'branch','codex/alpha')
        with self.assertRaises(ValueError):self.create()
        self.assertEqual(self.bindings,{})
    def test_remove_failure_does_not_mark_removed(self):
        record=self.create();real=core.git
        def fail(repo,*args):
            if args[:2]==('worktree','remove'):raise ValueError('injected')
            return real(repo,*args)
        with patch.object(core,'git',fail):
            with self.assertRaises(ValueError):self.retire()
        self.assertEqual(self.bindings['alpha']['status'],'ready');self.assertTrue(Path(record['path']).exists())
    def test_keep_busy_no_state_change(self):
        self.create();self.bindings['alpha']['active']=True
        self.assertEqual(core.retire_workspace(self.repo,self.parent,self.bindings,'alpha','keep',self.lock)['status'],'busy')
        self.assertEqual(self.bindings['alpha']['status'],'ready')

if __name__=='__main__':unittest.main()
