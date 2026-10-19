import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from practice import initialize,work
from runtime import create_task,claim_task,complete_task,load_board,save_board,ready_ids,checked_board,get_task,build_task_tools,execute_task_call
class TaskTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=self.root/'.tasks';initialize(self.store)
 def tearDown(self):self.temp.cleanup()
 def snapshot(self):return (self.store/'tasks.json').read_bytes()
 def check_done(self):claim_task(self.store,'check','worker-a');complete_task(self.store,'check','worker-a','已读文件，尚未运行。')
 def test_create_and_ready(self):
  self.assertEqual(ready_ids(load_board(self.store)),['check']);self.assertEqual(load_board(self.store)['revision'],3)
 def test_invalid_creation_preserves(self):
  for key,deps in [('check',[]),('next',['missing']),('next',['next']),('../escape',[]),('next',['check','check'])]:
   before=self.snapshot()
   with self.assertRaises(ValueError):create_task(self.store,key,'主题','说明',deps)
   self.assertEqual(self.snapshot(),before)
 def test_blocked(self):
  before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'依赖'):claim_task(self.store,'run','worker-a')
  self.assertEqual(self.snapshot(),before)
 def test_owner_and_state(self):
  claim_task(self.store,'check','worker-a');before=self.snapshot()
  for action in (lambda:claim_task(self.store,'check','worker-b'),lambda:complete_task(self.store,'check','worker-b','伪造结果'),lambda:complete_task(self.store,'run','worker-a','提前完成')):
   with self.assertRaises(ValueError):action()
   self.assertEqual(self.snapshot(),before)
 def test_unlock_only_new(self):
  create_task(self.store,'independent','独立记录','',[]);create_task(self.store,'review','复查记录','',['check'])
  claim_task(self.store,'check','worker-a');out=complete_task(self.store,'check','worker-a','已读文件')
  self.assertEqual(out['unlocked'],['review','run']);self.assertIn('independent',ready_ids(load_board(self.store)))
 def test_result_required(self):
  claim_task(self.store,'check','worker-a');before=self.snapshot()
  with self.assertRaises(ValueError):complete_task(self.store,'check','worker-a',' ')
  self.assertEqual(self.snapshot(),before)
 def test_atomic_failure(self):
  claim_task(self.store,'check','worker-a');before=self.snapshot()
  with patch('os.replace',side_effect=OSError('replace failed')):
   with self.assertRaises(OSError):complete_task(self.store,'check','worker-a','已读文件')
  self.assertEqual(self.snapshot(),before);self.assertEqual(list(self.store.glob('.tasks-*')),[])
 def test_corruption_and_cycle(self):
  for raw in ('{bad',json.dumps({'version':1,'revision':3,'tasks':{'check':None}})):
   (self.store/'tasks.json').write_text(raw);before=self.snapshot()
   with self.assertRaises(ValueError):claim_task(self.store,'check','worker-a')
   self.assertEqual(self.snapshot(),before)
  a={'id':'a','subject':'a','description':'','owner':None,'status':'pending','blocked_by':['b'],'result':''};b={**a,'id':'b','blocked_by':['a']}
  with self.assertRaisesRegex(ValueError,'环'):checked_board({'version':1,'revision':0,'tasks':{'a':a,'b':b}})
 def test_return_copy(self):
  item=claim_task(self.store,'check','worker-a');item['owner']='other';self.assertEqual(get_task(self.store,'check')['owner'],'worker-a')
 def test_limit_and_oversize(self):
  for n in range(17):create_task(self.store,'extra-'+str(n),'记录','',[])
  before=self.snapshot()
  with self.assertRaises(ValueError):create_task(self.store,'overflow','记录','',[])
  self.assertEqual(self.snapshot(),before)
  (self.store/'tasks.json').write_text(' '*64001)
  with self.assertRaisesRegex(ValueError,'64000'):load_board(self.store)
 def test_host_bound_owner_and_id(self):
  tools=build_task_tools(self.store,'worker-a');call={'id':'call_7','name':'task_claim','input':{'task_id':'check','owner':'worker-b'}}
  out=execute_task_call(call,tools,set(tools));self.assertTrue(out['is_error']);self.assertEqual(out['tool_use_id'],'call_7');self.assertIsNone(get_task(self.store,'check')['owner'])
 def test_three_new_processes(self):
  (self.root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n");(self.root/'expected.txt').write_text('42\n')
  script=Path(__file__).with_name('practice.py')
  for task in ('check','run','report'):
   p=subprocess.run([sys.executable,str(script),'work','--workspace',str(self.root),'--store',str(self.store),'--task',task,'--decision','allow'],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  self.assertEqual((self.root/'count').read_text(),'x');self.assertEqual(load_board(self.store)['revision'],9);self.assertEqual(ready_ids(load_board(self.store)),[])
 def test_deny_does_not_finish_or_resume(self):
  self.check_done();(self.root/'main.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\nprint(42)\n");(self.root/'expected.txt').write_text('42')
  with contextlib.redirect_stdout(io.StringIO()):out,_,_=work(self.root,self.store,'run',allowed=False)
  self.assertEqual(out['status'],'answered');self.assertEqual(get_task(self.store,'run')['status'],'in_progress');self.assertFalse((self.root/'ran').exists());before=self.snapshot()
  with contextlib.redirect_stdout(io.StringIO()):work(self.root,self.store,'run',allowed=True)
  self.assertEqual(self.snapshot(),before);self.assertFalse((self.root/'ran').exists())
 def test_wrong_output_does_not_unlock(self):
  self.check_done();(self.root/'main.py').write_text('print(41)');(self.root/'expected.txt').write_text('42')
  with contextlib.redirect_stdout(io.StringIO()):work(self.root,self.store,'run',allowed=True)
  self.assertEqual(get_task(self.store,'run')['status'],'in_progress');self.assertNotIn('report',ready_ids(load_board(self.store)))
if __name__=='__main__':unittest.main()
