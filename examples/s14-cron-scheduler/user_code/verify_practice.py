import contextlib
from datetime import datetime
import io
from pathlib import Path
import tempfile
import threading
import unittest
from practice import demo, run_check, serve
from runtime import cron_fields, cron_matches, enqueue_due, dispatch_next, new_state, schedule_job, cancel_job, build_schedule_tools, _s07

def at(value='09:05:00'):return datetime.fromisoformat('2026-10-19T'+value+'+08:00')
def configured(once=False):
    state,lock=new_state(),threading.RLock();schedule_job(state,lock,'*/5 * * * *','检查程序',once);return state,lock
class SchedulerTests(unittest.TestCase):
    def test_matching(self):
        self.assertTrue(cron_matches('*/5 * * * *',at()))
        self.assertFalse(cron_matches('*/5 * * * *',at('09:04:00')))
        self.assertTrue(cron_matches('0 9 1 * 1',at('09:00:00')))
        self.assertTrue(cron_matches('0 9 * * 0',datetime.fromisoformat('2026-10-18T01:00:00+00:00')))
        self.assertFalse(cron_matches('0 9 1 2 1',at('09:00:00')))
    def test_invalid(self):
        for expr in ('*/0 * * * *','*/60 * * * *','60 * * * *','0 24 * * *','0 9 0 * *','0 9 * 13 *','0 9 * * 7','*/5 * *','0 9 * * 1-5','0 9 * * 1,2'):
            with self.assertRaises(ValueError):cron_fields(expr)
        with self.assertRaises(ValueError):cron_matches('* * * * *',datetime(2026,10,19))
    def test_dedup_backward_and_next_day(self):
        state,lock=configured()
        self.assertEqual(len(enqueue_due(state,at(),lock)),1)
        self.assertEqual(enqueue_due(state,at('09:05:59'),lock),[])
        self.assertEqual(enqueue_due(state,at('09:00:00'),lock),[])
        self.assertEqual(len(enqueue_due(state,datetime.fromisoformat('2026-10-20T09:05:00+08:00'),lock)),1)
        self.assertEqual(len(state['queue']),2) # no backfill of missed minutes
    def test_full_does_not_ack(self):
        state,lock=configured();state['queue']=[{'id':str(i)} for i in range(8)]
        self.assertEqual(enqueue_due(state,at(),lock),[])
        self.assertIsNone(state['jobs']['cron-1']['last_slot'])
        state['queue'].pop();self.assertEqual(len(enqueue_due(state,at(),lock)),1)
    def test_once_and_cancel(self):
        state,lock=configured(True);enqueue_due(state,at(),lock)
        self.assertFalse(state['jobs']);self.assertEqual(len(state['queue']),1)
        cancel_job(state,lock,'cron-1');self.assertFalse(state['queue'])
        self.assertEqual(dispatch_next(state,lambda _:None,lock),{'status':'idle'})
    def test_busy_preserves_queue(self):
        state,lock=configured();enqueue_due(state,at(),lock)
        self.assertEqual(dispatch_next(state,lambda _:self.fail('called while busy'),lock,True),{'status':'busy'})
        self.assertEqual(len(state['queue']),1)
    def test_producer_continues_and_consumer_serial(self):
        state,lock=configured();enqueue_due(state,at(),lock);entered=threading.Event();release=threading.Event();outputs=[]
        def turn(event):
            entered.set();self.assertTrue(release.wait(2));return {'status':'answered','text':event['id']}
        worker=threading.Thread(target=lambda:outputs.append(dispatch_next(state,turn,lock)));worker.start()
        try:
            self.assertTrue(entered.wait(2));self.assertEqual(len(enqueue_due(state,at('09:10:00'),lock)),1)
            self.assertEqual(dispatch_next(state,lambda _:None,lock),{'status':'busy'})
        finally:release.set();worker.join(2)
        self.assertFalse(worker.is_alive());self.assertIsNone(state['active']);self.assertEqual(len(state['results']),1)
    def test_failed_turn_no_retry_and_release(self):
        state,lock=configured();enqueue_due(state,at(),lock)
        def fail(_):raise OSError('fixed')
        self.assertEqual(dispatch_next(state,fail,lock)['status'],'turn_error')
        self.assertFalse(state['queue']);self.assertIsNone(state['active'])
        self.assertEqual(dispatch_next(state,fail,lock)['status'],'idle')
    def test_interrupt_records_and_releases(self):
        state,lock=configured();enqueue_due(state,at(),lock)
        def fail(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):dispatch_next(state,fail,lock)
        self.assertIsNone(state['active']);self.assertEqual(state['results'][-1]['status'],'interrupted')
    def test_registration_tools(self):
        state,lock=new_state(),threading.RLock();tools=build_schedule_tools(state,lock)
        for name,args in [('schedule_cron',{'cron':'*/5 * * * *','prompt':'检查'}),('list_crons',{}),('cancel_cron',{'job_id':'cron-1'})]:
            result=_s07._s02.execute_tool({'id':'c','name':name,'input':args},tools);self.assertFalse(result['is_error'])
        self.assertFalse(state['jobs'])
        for _ in range(3):schedule_job(state,lock,'* * * * *','检查')
        with self.assertRaises(ValueError):schedule_job(state,lock,'* * * * *','检查')
    def test_real_twice_and_deny(self):
        for allowed in (True,False):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'expected.txt').write_text('42')
                (root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
                with contextlib.redirect_stdout(io.StringIO()):state=demo(root,allowed)
                self.assertEqual(len(state['results']),2);self.assertFalse(state['queue'])
                self.assertEqual((root/'count').read_text() if (root/'count').exists() else '', 'xx' if allowed else '')
                self.assertTrue(all(('exit_code=0' in row['text'])==allowed for row in state['results']))
    def test_serve_stops_thread(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'expected.txt').write_text('42');(root/'main.py').write_text('print(42)')
            with contextlib.redirect_stdout(io.StringIO()):state=serve(root,False,.05)
            self.assertFalse(any(t.name=='s14-clock' for t in threading.enumerate()))
            self.assertIsNone(state['active'])
if __name__=='__main__':unittest.main()
