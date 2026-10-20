from copy import deepcopy
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from practice import demo,finish_job,run_job
from runtime import *
from runtime import _tasks,_s16,_s11

class AutonomousTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.directory=self.root/'board';self.mail=self.root/'mail';self.team=create_team();self.state={};self.lock=threading.RLock()
 def tearDown(self):self.tmp.cleanup()
 def task(self,key='source',deps=()):return create_task(self.directory,key,key,'固定文件',list(deps))
 def test_full_concurrent_paths_and_actual_evidence(self):
  for index,(allowed,expected) in enumerate([(True,'42'),(False,'42'),(True,'43')]):
   work=self.root/str(index);work.mkdir();(work/'expected.txt').write_text(expected);(work/'main.py').write_text("from pathlib import Path\np=Path('count')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
   barrier=threading.Barrier(2);first=[];gate=threading.Lock()
   def claimed(actor,task):
    if task['id'] in ('source','expected'):
     with gate:first.append((actor,task['id']))
     barrier.wait(3)
   result=demo(self.root/('state'+str(index)),work,allowed,on_claim=claimed)
   self.assertEqual(len({x[0] for x in first}),2);self.assertEqual(len({x[1] for x in first}),2)
   self.assertEqual(len(result['reports']),3);self.assertEqual(len(result['traces']),7)
   board=result['board'];self.assertEqual(board['tasks']['verify']['status'],'completed' if allowed and expected=='42' else 'in_progress')
   self.assertEqual((work/'count').exists(),allowed)
   if allowed:self.assertEqual((work/'count').read_text(),'x')
   self.assertTrue(all(t['status']=='closed' for n,t in result['team'].items() if n!='lead'))
   self.assertEqual(load_board(self.root/('state'+str(index))/'board'),board)
   self.assertIn('task_id',str(result['traces'][-1]['request']['messages']))
 def test_one_task_two_workers_only_one_claim(self):
  self.task();barrier=threading.Barrier(2);results=[]
  def pick(name):barrier.wait(3);results.append(claim_next(self.directory,self.team,name,self.lock))
  threads=[threading.Thread(target=pick,args=(n,)) for n in ('reader','reviewer')]
  for t in threads:t.start()
  for t in threads:t.join(3)
  self.assertTrue(all(not t.is_alive() for t in threads));self.assertEqual(sorted(x['status'] for x in results),['claimed','idle']);self.assertEqual(load_board(self.directory)['revision'],2)
 def test_stale_scan_cannot_steal_claim(self):
  self.task();self.task('expected');snapshot=load_board(self.directory);self.assertEqual(scan_ready(snapshot),['expected','source'])
  first=claim_next(self.directory,self.team,'reviewer',self.lock);second=claim_next(self.directory,self.team,'reader',self.lock)
  self.assertEqual(first['task']['id'],'expected');self.assertEqual(second['task']['id'],'source');self.assertIsNone(snapshot['tasks']['expected']['owner'])
 def test_dependencies_rechecked_after_completion(self):
  self.task();self.task('verify',['source']);claimed=claim_next(self.directory,self.team,'reader',self.lock);self.assertEqual(claimed['task']['id'],'source');self.assertEqual(claim_next(self.directory,self.team,'reviewer',self.lock)['status'],'idle')
  with self.lock:complete_task(self.directory,'source','reader','actual-source')
  self.assertEqual(claim_next(self.directory,self.team,'reviewer',self.lock)['task']['id'],'verify')
 def test_owned_active_closed_and_delivery_limit(self):
  self.task();claim_next(self.directory,self.team,'reader',self.lock);self.assertEqual(claim_next(self.directory,self.team,'reader',self.lock)['status'],'busy')
  for change in ({'active':True},{'status':'closed'},{'turns':2}):
   team=create_team();team['reviewer'].update(change);self.assertEqual(claim_next(self.directory,team,'reviewer',self.lock)['status'],'unavailable')
 def test_claim_save_failure_keeps_bytes(self):
  self.task();before=(self.directory/'tasks.json').read_bytes()
  with patch.object(_tasks.os,'replace',side_effect=OSError('disk')):
   with self.assertRaises(OSError):claim_next(self.directory,self.team,'reader',self.lock)
  self.assertEqual((self.directory/'tasks.json').read_bytes(),before);self.assertEqual(list(self.directory.glob('.tasks-*')),[])
 def test_wait_releases_lock_and_new_task_wakes(self):
  entered,release=threading.Event(),threading.Event();results=[]
  def wait(_):entered.set();self.assertTrue(release.wait(3));return False
  thread=threading.Thread(target=lambda:results.append(idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,wait,2)));thread.start()
  try:
   self.assertTrue(entered.wait(3));self.assertTrue(self.lock.acquire(timeout=1))
   try:self.task()
   finally:self.lock.release()
  finally:release.set();thread.join(3)
  self.assertFalse(thread.is_alive());self.assertEqual(results[0]['status'],'claimed')
 def test_shutdown_precedes_ready_board_even_at_limit(self):
  self.task();self.team['reader']['turns']=2;key=open_request(self.state,self.team,self.mail,'lead','reader','shutdown','空闲确认关闭',self.lock)['request_id']
  outcome=idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,lambda _:False,1)
  self.assertEqual(outcome['status'],'shutdown');self.assertEqual(self.team['reader']['status'],'closed');self.assertEqual(load_board(self.directory)['tasks']['source']['status'],'pending');self.assertEqual(self.state[key]['status'],'pending')
  consume_responses(self.state,self.team,self.mail,'lead',self.lock);self.assertEqual(self.state[key]['status'],'approved')
 def test_shutdown_during_actual_wait_prevents_claim(self):
  entered,release=threading.Event(),threading.Event();results=[]
  def wait(_):entered.set();self.assertTrue(release.wait(3));return False
  thread=threading.Thread(target=lambda:results.append(idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,wait,2)));thread.start()
  try:
   self.assertTrue(entered.wait(3))
   with self.lock:self.task();open_request(self.state,self.team,self.mail,'lead','reader','shutdown','关闭优先',self.lock)
  finally:release.set();thread.join(3)
  self.assertFalse(thread.is_alive());self.assertEqual(results[0]['status'],'shutdown');self.assertIsNone(load_board(self.directory)['tasks']['source']['owner'])
 def test_shutdown_save_failure_does_not_claim(self):
  self.task();key=open_request(self.state,self.team,self.mail,'lead','reader','shutdown','关闭优先',self.lock)['request_id'];before=(self.directory/'tasks.json').read_bytes()
  with patch.object(_tasks.os,'replace',side_effect=OSError('disk')):
   with self.assertRaises(OSError):idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,lambda _:False,1)
  self.assertEqual((self.directory/'tasks.json').read_bytes(),before);self.assertEqual(self.team['reader']['status'],'idle');self.assertIsNone(self.state[key]['reply'])
 def test_timeout_and_interrupt_make_no_model_requests(self):
  waits=[]
  with patch.object(_s11,'request_with_recovery',side_effect=AssertionError('idle model')):
   out=idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,lambda n:waits.append(n),3)
  self.assertEqual(out,{'status':'idle_timeout','checks':3});self.assertEqual(waits,[.05,.05]);self.assertEqual(self.team['reader']['status'],'idle')
  self.assertEqual(idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,lambda _:True,2)['status'],'interrupted')
  for checks in (0,13,True,1.0):
   with self.assertRaises(ValueError):idle_poll(self.directory,self.team,self.state,self.mail,'reader',self.lock,lambda _:False,checks)
 def test_invalid_board_preserved_and_scan_readonly(self):
  self.task();board=load_board(self.directory);before=deepcopy(board);self.assertEqual(scan_ready(board),['source']);self.assertEqual(board,before)
  board['tasks']['source']['blocked_by']=['missing']
  with self.assertRaises(ValueError):scan_ready(board)
  (self.directory/'tasks.json').write_text('bad-json')
  with self.assertRaises(ValueError):claim_next(self.directory,self.team,'reader',self.lock)
  self.assertEqual((self.directory/'tasks.json').read_text(),'bad-json')
 def test_wrong_tool_path_is_not_completion(self):
  self.task();task=claim_next(self.directory,self.team,'reader',self.lock)['task'];work=self.root/'work';work.mkdir();(work/'main.py').write_text('print(42)');(work/'expected.txt').write_text('secret')
  requests=[]
  def send(req):
   if len(requests)==0:
    from runtime import _s10
    response=_s10.use('read_file',{'path':'expected.txt'},1)
   else:
    from runtime import _s10
    response=_s10.answer('工具被拒绝。')
   requests.append(req);return response
  outcome=run_job([],'reader',task,self.directory,self.mail,self.team,work,False,self.lock,[],send)
  self.assertTrue(outcome['evidence']['is_error']);self.assertNotIn('secret',outcome['evidence']['content']);self.assertEqual(finish_job(self.directory,task,'reader',outcome,self.lock)['status'],'needs_attention');self.assertEqual(load_board(self.directory)['tasks']['source']['status'],'in_progress')

if __name__=='__main__':unittest.main()
