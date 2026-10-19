from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from practice import demo, fixed_model
from runtime import create_team, send_message, prepare_inbox, run_teammate, load_inbox, message_tool, _s07

class TeamTests(unittest.TestCase):
    def test_real_team_and_retained_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);workspace=root/'work';workspace.mkdir()
            (workspace/'main.py').write_text("from pathlib import Path\nPath('should-not-run').write_text('x')\nprint(6*7)\n")
            (workspace/'expected.txt').write_text('42')
            team,reports,lead,traces=demo(root/'mail',workspace)
            self.assertTrue(all(r['status']=='answered' for r in reports));self.assertEqual(len(traces),9)
            self.assertEqual(team['reader']['turns'],2);self.assertFalse((workspace/'should-not-run').exists())
            self.assertEqual(len(load_inbox(root/'mail','lead',team)),2)
            second=[t['request'] for t in traces if t['actor']=='reader' and t['phase']==2]
            self.assertEqual(len(second),2)
            self.assertIn('reader-1-1',str(second[0]['messages']))
            self.assertIn('reviewer',str(second[0]['messages']))
            self.assertFalse(any(b.get('name')=='read_file' for m in second[-1]['messages'][-3:] if isinstance(m['content'],list) for b in m['content']))
            for req in second:
                notices=[m['content'] for m in req['messages'] if isinstance(m['content'],str) and m['content'].startswith('[team-message] ')]
                self.assertEqual(len(notices),len(set(notices)))
            self.assertTrue(all(not m['active'] for m in team.values()))
    def test_notice_after_result_does_not_replace_tool_evidence(self):
        history=[{'role':'user','content':'[team-turn] reader:1\n读取源码'},
                 {'role':'assistant','content':[{'type':'tool_use','id':'reader-1-1','name':'read_file','input':{'path':'main.py'}}]},
                 {'role':'user','content':[{'type':'tool_result','tool_use_id':'reader-1-1','content':'print(6*7)','is_error':False}]},
                 {'role':'user','content':'[team-message] '+json.dumps({'sender':'reviewer','body':'预期42'})}]
        response=fixed_model(history,'reader')
        self.assertEqual(response['content'][0]['name'],'send_message')
        self.assertIn('print(6*7)',response['content'][0]['input']['body'])
    def test_concurrent_senders(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock()
            with ThreadPoolExecutor(max_workers=8) as pool:
                results=list(pool.map(lambda i:send_message(d,team,'reader' if i%2 else 'reviewer','lead',str(i),lock),range(8)))
            records=load_inbox(d,'lead',team)
            self.assertEqual(len(records),8);self.assertEqual(len({r['id'] for r in results}),8)
            self.assertEqual({r['body'] for r in records},{str(i) for i in range(8)})
    def test_full_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock()
            for i in range(8):send_message(d,team,'reader','lead',str(i),lock)
            old=(Path(d)/'lead.jsonl').read_bytes()
            with self.assertRaises(ValueError):send_message(d,team,'reader','lead','ninth',lock)
            self.assertEqual((Path(d)/'lead.jsonl').read_bytes(),old)
    def test_replace_failure_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock();send_message(d,team,'reader','lead','old',lock)
            old=(Path(d)/'lead.jsonl').read_bytes()
            with patch('os.replace',side_effect=OSError('fixed')):
                with self.assertRaises(OSError):send_message(d,team,'reader','lead','new',lock)
            self.assertEqual((Path(d)/'lead.jsonl').read_bytes(),old)
            self.assertEqual([p.name for p in Path(d).iterdir()],['lead.jsonl'])
    def test_names_corruption_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock()
            for sender,recipient,body in [('unknown','lead','x'),('reader','../escape','x'),('reader','lead',''),('reader','lead','x'*601)]:
                with self.assertRaises(ValueError):send_message(d,team,sender,recipient,body,lock)
            p=Path(d)/'lead.jsonl';p.write_text('bad-json')
            with self.assertRaises(ValueError):prepare_inbox([],d,team,'lead',lock)
            self.assertEqual(p.read_text(),'bad-json')
            p.write_text('x'*32001)
            with self.assertRaises(ValueError):prepare_inbox([],d,team,'lead',lock)
    def test_no_delete_candidate_retry_and_new_arrival(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock();send_message(d,team,'reader','lead','first',lock)
            history=[{'role':'user','content':'q'}];first=prepare_inbox(history,d,team,'lead',lock)
            self.assertEqual(prepare_inbox(history,d,team,'lead',lock),first)
            send_message(d,team,'reviewer','lead','second',lock)
            final=prepare_inbox(first,d,team,'lead',lock)
            self.assertEqual(len(final),3);self.assertEqual(prepare_inbox(final,d,team,'lead',lock),final)
            self.assertEqual(len(load_inbox(d,'lead',team)),2);self.assertEqual(len(history),1)
    def test_history_limit(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock();send_message(d,team,'reader','lead','x',lock)
            history=[{'role':'user','content':'q'}]*80
            with self.assertRaises(ValueError):prepare_inbox(history,d,team,'lead',lock)
            self.assertEqual(len(history),80);self.assertEqual(len(load_inbox(d,'lead',team)),1)
    def test_same_member_serial_other_member_parallel(self):
        team,lock=create_team(),threading.RLock();ready=[threading.Event(),threading.Event()];release=threading.Event();results=[]
        def callback(index):
            def work(history):
                ready[index].set();self.assertTrue(release.wait(2));return {'status':'answered','text':'ok','messages':history+[{'role':'assistant','content':'ok'}]}
            return work
        workers=[threading.Thread(target=lambda i=i:results.append(run_teammate(team,['reader','reviewer'][i],callback(i),lock))) for i in range(2)]
        try:
            for worker in workers:worker.start()
            self.assertTrue(all(event.wait(2) for event in ready))
            self.assertEqual(run_teammate(team,'reader',lambda _:self.fail('duplicate'),lock)['status'],'unavailable')
        finally:
            release.set()
            for worker in workers:worker.join(2)
        self.assertEqual(len(results),2);self.assertTrue(all(not m['active'] for m in team.values()))
    def test_two_deliveries_then_stop(self):
        team,lock=create_team(),threading.RLock()
        def work(history):return {'status':'answered','text':'ok','messages':history+[{'role':'assistant','content':'ok'}]}
        for _ in range(2):self.assertEqual(run_teammate(team,'reader',work,lock)['status'],'answered')
        self.assertEqual(len(team['reader']['history']),2)
        self.assertEqual(run_teammate(team,'reader',work,lock)['status'],'unavailable')
    def test_failed_or_invalid_preserves_history(self):
        for kind in ('exception','invalid'):
            team,lock=create_team(),threading.RLock();team['reader']['history']=[{'role':'user','content':'old'}]
            before=deepcopy(team['reader']['history'])
            def work(history):
                history.append({'role':'user','content':'candidate'})
                if kind=='exception':raise OSError('fixed')
                return {'messages':history}
            self.assertEqual(run_teammate(team,'reader',work,lock)['status'],'failed')
            self.assertEqual(team['reader']['history'],before);self.assertFalse(team['reader']['active'])
    def test_call_limit_and_interrupt_release(self):
        team,lock=create_team(),threading.RLock()
        result=run_teammate(team,'reader',lambda h:{'status':'call_limit','text':'limit','messages':h},lock)
        self.assertEqual(result['status'],'call_limit');self.assertEqual(team['reader']['status'],'stopped')
        def interrupt(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):run_teammate(team,'reviewer',interrupt,lock)
        self.assertFalse(team['reviewer']['active']);self.assertEqual(team['reviewer']['status'],'stopped')
    def test_bound_sender_and_read_only_tools(self):
        with tempfile.TemporaryDirectory() as d:
            team,lock=create_team(),threading.RLock();tools={'send_message':message_tool(d,team,'reader',lock)}
            self.assertNotIn('sender',tools['send_message']['parameters'])
            result=_s07._s02.execute_tool({'id':'x','name':'send_message','input':{'recipient':'lead','body':'message'}},tools)
            self.assertFalse(result['is_error']);self.assertEqual(load_inbox(d,'lead',team)[0]['sender'],'reader')
            result=_s07._s02.execute_tool({'id':'y','name':'run_main','input':{}},tools)
            self.assertTrue(result['is_error'])
if __name__=='__main__':unittest.main()
