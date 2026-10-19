import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from practice import demo
from runtime import *

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.mail=self.root/'mail';self.team=create_team();self.state={};self.lock=threading.RLock()
    def tearDown(self):self.tmp.cleanup()
    def opened(self,kind='plan'):
        a,b=('reader','lead') if kind=='plan' else ('lead','reader')
        return open_request(self.state,self.team,self.mail,a,b,kind,'本次固定计划',self.lock)['request_id']
    def reply(self,key,approve=True):return reply_request(self.state,self.team,self.mail,key,self.state[key]['target'],approve,'决定',self.lock)
    def message(self,key):return load_inbox(self.mail,self.state[key]['sender'],self.team)[-1]
    def test_full_paths_real_program_or_denial(self):
        for index,(approved,allowed) in enumerate([(True,True),(True,False),(False,True)]):
            work=self.root/str(index);work.mkdir();marker=work/'executed';(work/'expected.txt').write_text('42');(work/'main.py').write_text("from pathlib import Path\np=Path('executed')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
            result=demo(self.root/('mail'+str(index)),work,approved,allowed)
            self.assertEqual(marker.exists(),approved and allowed)
            if marker.exists():self.assertEqual(marker.read_text(),'x');self.assertIn('42',result['work']['text'])
            self.assertEqual(result['pending_before'],'pending');self.assertEqual(result['shutdown_before'],'pending');self.assertEqual(result['team']['reader']['status'],'closed');self.assertEqual(result['blocked']['status'],'unavailable')
            self.assertEqual(len(result['traces']),7);self.assertIn('reader-plan-1',str(result['team']['reader']['history']))
    def test_actual_output_mismatch_is_not_success_claim(self):
        work=self.root/'mismatch';work.mkdir();(work/'expected.txt').write_text('43');(work/'main.py').write_text('print(42)')
        result=demo(self.mail,work,True,True)
        self.assertIn('与预期不符',result['work']['text'])
    def test_save_failure_keeps_request_and_member(self):
        import runtime
        with patch.object(runtime._s15.os,'replace',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.opened()
        self.assertEqual(self.state,{})
        key=self.opened('shutdown');old=deepcopy(self.state)
        with patch.object(runtime._s15.os,'replace',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.reply(key)
        self.assertEqual(self.state,old);self.assertEqual(self.team['reader']['status'],'idle')
    def test_reply_saved_not_yet_matched_and_duplicate(self):
        key=self.opened();self.reply(key);self.assertEqual(self.state[key]['status'],'pending');message=self.message(key)
        self.assertEqual(match_response(self.state,message,'reader',self.lock)['status'],'approved')
        self.assertEqual(match_response(self.state,message,'reader',self.lock)['status'],'duplicate')
        self.assertEqual(self.reply(key)['status'],'already_sent');self.assertEqual(len(load_inbox(self.mail,'reader',self.team)),1)
        with self.assertRaises(ValueError):self.reply(key,False)
    def test_wrong_id_type_role_recipient_or_unsaved_reply(self):
        key=self.opened();self.reply(key);original=self.message(key)
        for field,value in [('type','shutdown_response'),('request_id','req-404'),('approve','true'),('feedback','not-saved')]:
            message=deepcopy(original);data=read_protocol(message);data[field]=value;message['body']=encode_protocol(data)
            self.assertEqual(match_response(self.state,message,'reader',self.lock)['status'],'ignored');self.assertEqual(self.state[key]['status'],'pending')
        for field,value in [('sender','reviewer'),('recipient','reviewer')]:
            message=deepcopy(original);message[field]=value;self.assertEqual(match_response(self.state,message,'reader',self.lock)['status'],'ignored')
        self.assertEqual(match_response(self.state,original,'lead',self.lock)['status'],'ignored')
    def test_shutdown_waits_for_real_active_turn(self):
        started,release=threading.Event(),threading.Event()
        def turn(history):started.set();self.assertTrue(release.wait(3));return {'messages':history,'status':'answered','text':'done'}
        thread=threading.Thread(target=lambda:run_teammate(self.team,'reader',turn,self.lock));thread.start()
        try:
            self.assertTrue(started.wait(3));key=self.opened('shutdown');self.assertEqual(self.reply(key)['status'],'deferred');self.assertTrue(self.team['reader']['active']);self.assertIsNone(self.state[key]['reply'])
        finally:release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.reply(key);self.assertEqual(self.team['reader']['status'],'closed');self.assertEqual(self.state[key]['status'],'pending');self.assertEqual(match_response(self.state,self.message(key),'lead',self.lock)['status'],'approved')
    def test_shutdown_reject_keeps_member_available(self):
        key=self.opened('shutdown');self.reply(key,False);self.assertEqual(self.team['reader']['status'],'idle');self.assertEqual(match_response(self.state,self.message(key),'lead',self.lock)['status'],'rejected')
    def test_direction_capacity_and_payload(self):
        for a,b,k in [('lead','reader','plan'),('reader','lead','shutdown'),('reader','reviewer','plan')]:
            with self.assertRaises(ValueError):open_request(self.state,self.team,self.mail,a,b,k,'x',self.lock)
        with self.assertRaises(ValueError):open_request(self.state,self.team,self.mail,'reader','lead','plan',' '*2,self.lock)
        key=self.opened()
        with self.assertRaises(ValueError):self.opened()
        self.reply(key);match_response(self.state,self.message(key),'reader',self.lock)
        for _ in range(3):
            key=self.opened();self.reply(key);match_response(self.state,self.message(key),'reader',self.lock)
        with self.assertRaises(ValueError):self.opened()
    def test_concurrent_replies_only_one_decision(self):
        key=self.opened();results=[]
        def reply(approved):
            try:results.append(self.reply(key,approved))
            except ValueError:results.append({'error':True})
        threads=[threading.Thread(target=reply,args=(x,)) for x in (True,False)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(sum('error' in x for x in results),1);self.assertEqual(len(load_inbox(self.mail,'reader',self.team)),1)
    def test_consume_does_not_delete_and_ignores_malformed(self):
        key=self.opened();self.reply(key);send_message(self.mail,self.team,'lead','reader','[team-protocol] bad-json',self.lock)
        consume_responses(self.state,self.team,self.mail,'reader',self.lock);self.assertEqual(self.state[key]['status'],'approved');self.assertEqual(len(load_inbox(self.mail,'reader',self.team)),2)
        self.assertEqual(consume_responses(self.state,self.team,self.mail,'reader',self.lock)[0]['status'],'duplicate')
    def test_gate_bound_to_exact_plan_and_actor(self):
        key=self.opened();gate=plan_gate(self.state,key,'reader',self.lock);call={'call':{'name':'run_main'}}
        self.assertIsNotNone(gate(call));self.reply(key);match_response(self.state,self.message(key),'reader',self.lock);self.assertIsNone(gate(call));self.assertIsNotNone(plan_gate(self.state,key,'reviewer',self.lock)(call));self.assertIsNotNone(plan_gate(self.state,'req-404','reader',self.lock)(call))

if __name__=='__main__':unittest.main()
