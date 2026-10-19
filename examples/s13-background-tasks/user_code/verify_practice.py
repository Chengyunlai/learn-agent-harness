import contextlib
import io
from pathlib import Path
import tempfile
import time
import unittest
from practice import run
from runtime import ProcessHandle, start_background, collect_background, prepare_background

class BackgroundTests(unittest.TestCase):
    def test_real_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'expected.txt').write_text('42')
            (root/'main.py').write_text("from pathlib import Path\nimport time\nPath('started').write_text('x')\nwhile not Path('release').exists(): time.sleep(.005)\nprint(42)\n")
            def release(jobs):
                (root/'release').write_text('yes')
                jobs['step_1']['handle'].process.wait(timeout=2)
            with contextlib.redirect_stdout(io.StringIO()):out, final, requests, jobs = run(root, True, after_read=release)
            assert out['status'] == 'answered' and len(requests) == 3
            assert jobs['step_1']['result']['output'] == '42'
            assert '[background-result]' in str(requests[-1]['messages'])
            assert (root/'started').read_text() == 'x'
            assert sum(b.get('type')=='tool_result' and b['tool_use_id']=='step_1' for m in final if isinstance(m['content'],list) for b in m['content'])==1
    def test_deny_and_limit(self):
        for allowed, limit in ((False,4),(True,1)):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'main.py').write_text('print(42)');(root/'expected.txt').write_text('42')
                with contextlib.redirect_stdout(io.StringIO()):out,final,requests,jobs=run(root,allowed,max_calls=limit)
                assert len(jobs)==int(allowed)
                assert out['status']==('call_limit' if limit==1 else 'answered')
                assert all(j['handle'].process.poll() is not None for j in jobs.values())
    def test_process_errors_and_cleanup(self):
        for source, timeout, status, error in [('print(10/0)',3,'completed',True),('import time; time.sleep(10)',.02,'timeout',True),('print(42)',3,'completed',False)]:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'main.py').write_text(source);h=ProcessHandle(root,timeout)
                try:
                    deadline=time.monotonic()+4;result=None
                    while result is None and time.monotonic()<deadline:result=h.snapshot();time.sleep(.005)
                    assert result['status']==status and result['is_error']==error
                    assert h.snapshot()==result
                finally:h.close()
    def test_discarded_candidate_keeps_notification(self):
        class Handle:
            def snapshot(self):return {'status':'completed','exit_code':0,'output':'42','is_error':False}
        jobs={};call={'id':'x','name':'run_background','input':{}}
        start_background(call,jobs,Handle,True);history=[{'role':'user','content':'q'}]
        first=prepare_background(history,jobs);second=prepare_background(history,jobs)
        assert first==second and len(history)==1
        assert prepare_background(first,jobs)==first
        first[-1]['content']='changed'
        assert collect_background(jobs)[0]['output']=='42'
    def test_pending_exit_no_model_polling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'main.py').write_text("from pathlib import Path\nimport time\nwhile not Path('release').exists():time.sleep(.005)\nprint(42)");(root/'expected.txt').write_text('42')
            from practice import fixed_model
            def send(payload):
                response=fixed_model(payload['messages'])
                if response['stop_reason']=='end_turn':(root/'release').write_text('yes')
                return response
            with contextlib.redirect_stdout(io.StringIO()):out,final,requests,jobs=run(root,True,send_override=send)
            assert len(requests)==3 and len(final)==len(out['messages'])+1
            assert out['text'].startswith('程序还在运行')
if __name__=='__main__':unittest.main()
