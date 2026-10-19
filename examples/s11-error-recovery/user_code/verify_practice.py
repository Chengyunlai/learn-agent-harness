import contextlib
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from practice import run
from runtime import classify_failure,retry_delay,request_with_recovery,RecoveryStopped
READY={'stop_reason':'end_turn','content':[{'type':'text','text':'ok'}]}
class RecoveryTests(unittest.TestCase):
 def invoke(self,queue,remaining=20):
  state={'remaining':remaining,'waited':0.,'events':[]};requests=[];waits=[]
  def send(p):requests.append(p);return deepcopy(queue.pop(0))
  return request_with_recovery(send,{'messages':[{'role':'user','content':'q'}],'max_tokens':1024},state,pause=waits.append,random_unit=lambda:0),state,requests,waits
 def test_classification(self):
  for status in (429,500,502,503,504,529):self.assertEqual(classify_failure({'failure':{'status':status}})['action'],'wait')
  for status in (400,401,403,404,413):self.assertEqual(classify_failure({'failure':{'status':status}})['action'],'stop')
  for data in (None,[],{}, {'stop_reason':'tool_use','content':[]}):self.assertEqual(classify_failure(data)['action'],'stop')
 def test_transport(self):
  for kind in ('connection','timeout'):self.assertEqual(classify_failure({'failure':{'transport':kind}})['action'],'wait')
 def test_header(self):
  self.assertEqual(retry_delay(0,'0'),0);self.assertEqual(retry_delay(3,'9'),9)
  for bad in ('bad','nan','inf',-1,True):self.assertEqual(retry_delay(1,bad,0),.5)
 def test_jitter(self):
  self.assertEqual(retry_delay(1,None,1),.625)
  for bad in (-1,float('nan'),2,True):
   with self.assertRaises(ValueError):retry_delay(0,None,bad)
 def test_transient(self):
  out,state,sent,waits=self.invoke([{'failure':{'status':529}},READY]);self.assertEqual(sent[0],sent[1]);self.assertEqual(waits,[.25]);self.assertEqual(state['remaining'],18)
 def test_truncation(self):
  partial={'stop_reason':'max_tokens','content':[{'type':'tool_use','id':'bad','name':'run_main','input':{}}]}
  _,_,sent,waits=self.invoke([partial,READY]);self.assertEqual([r['max_tokens'] for r in sent],[1024,2048]);self.assertEqual(sent[0]['messages'],sent[1]['messages']);self.assertEqual(waits,[])
 def test_no_retry_on_fatal(self):
  with self.assertRaisesRegex(RecoveryStopped,'401'):self.invoke([{'failure':{'status':401}}])
 def test_twice(self):
  with self.assertRaisesRegex(RecoveryStopped,'still_truncated'):self.invoke([{'stop_reason':'max_tokens'}]*2)
 def test_wait_budget(self):
  with self.assertRaisesRegex(RecoveryStopped,'wait_budget'):self.invoke([{'failure':{'status':429,'retry_after':'9'}}])
 def test_attempt_budget(self):
  with self.assertRaisesRegex(RecoveryStopped,'request_budget'):self.invoke([{'failure':{'status':529}}]*4)
 def test_session_budget(self):
  with self.assertRaisesRegex(RecoveryStopped,'request_budget'):self.invoke([],remaining=0)
 def test_copy_and_pause_failure(self):
  req={'messages':[{'role':'user','content':'q'}],'max_tokens':1024};before=deepcopy(req);state={'remaining':20,'waited':0.,'events':[]}
  def send(p):p['messages'].clear();return {'failure':{'status':529}}
  def broken(_):raise OSError('wait interrupted')
  with self.assertRaises(OSError):request_with_recovery(send,req,state,pause=broken,random_unit=lambda:0)
  self.assertEqual(req,before);self.assertEqual(state['remaining'],19);self.assertEqual(state['waited'],.25)
 def test_real_program_runs_once(self):
  for scenario in ('transient','truncated','truncated_twice','fatal','long_wait','exhausted'):
   with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as name:
    root=Path(name);(root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n");(root/'expected.txt').write_text('42\n')
    with contextlib.redirect_stdout(io.StringIO()):out,state,sent,waits=run(root,scenario,True)
    self.assertEqual((root/'count').read_text() if (root/'count').exists() else '', '' if scenario=='exhausted' else 'x')
    self.assertEqual(out['status'],'answered' if scenario in ('transient','truncated') else 'model_error')
    self.assertNotIn('partial',str(out['messages']))
    if scenario!='exhausted':self.assertIn('exit_code=0',str(out['messages']))
 def test_permission_not_recovered(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);(root/'main.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\nprint(42)\n");(root/'expected.txt').write_text('42')
   with contextlib.redirect_stdout(io.StringIO()):out,state,_,_=run(root,allowed=False)
   self.assertFalse((root/'ran').exists());self.assertEqual(out['status'],'answered');self.assertTrue(all(x['action']=='accept' for x in state['events']))
if __name__=='__main__':unittest.main()
