"""固定SDK+模拟HTTP；定时触发不授予程序许可，请求恢复不重跑。"""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import threading
import httpx2 as httpx
from anthropic import Anthropic
from practice import run_check, fixed_model
from runtime import new_state, schedule_job, enqueue_due, dispatch_next, _s11
for allowed in (True,False):
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);(root/'expected.txt').write_text('42')
        (root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
        requests=[];failed=False;state,lock=new_state(),threading.RLock()
        schedule_job(state,lock,'*/5 * * * *','读取预期，获准后运行程序。')
        enqueue_due(state,datetime.fromisoformat('2026-10-19T09:00:00+08:00'),lock)
        def handle(request):
            global failed
            payload=json.loads(request.content);requests.append(payload)
            after_run=any(isinstance(m['content'],list) and any(b.get('type')=='tool_result' and b.get('tool_use_id')=='step_2' for b in m['content']) for m in payload['messages'])
            if allowed and after_run and not failed:
                failed=True;return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
            return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(payload['messages'])})
        with Anthropic(api_key='placeholder',max_retries=0,timeout=20,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            with contextlib.redirect_stdout(io.StringIO()):out=dispatch_next(state,lambda event:run_check(event,root,allowed,lambda req:_s11.sdk_send(client,req)),lock)
        assert out['status']=='answered' and len(requests)==(4 if allowed else 3)
        assert requests[0]['messages'][0]['content'].startswith('[scheduled] cron-1@')
        assert (root/'count').exists()==allowed
        if allowed:assert (root/'count').read_text()=='x' and requests[-1]==requests[-2]
        assert not state['queue'] and state['active'] is None
        print('PASS SDK',allowed,len(requests),'HTTP; one event, process once or denied')
