"""真实SDK、模拟HTTP；后台程序真实执行，恢复不重新启动进程。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import run, fixed_model
from runtime import _s11
for allowed in (True, False):
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);(root/'expected.txt').write_text('42')
        (root/'main.py').write_text("from pathlib import Path\nimport time\nPath('count').write_text('x')\nwhile not Path('release').exists():time.sleep(.005)\nprint(42)\n")
        requests=[]; failed=False
        def release(jobs):
            (root/'release').write_text('yes');jobs['step_1']['handle'].process.wait(timeout=2)
        def handle(request):
            global failed
            payload=json.loads(request.content);requests.append(payload)
            notices=[m for m in payload['messages'] if isinstance(m['content'],str) and m['content'].startswith('[background-result] ')]
            if notices and not failed:
                failed=True
                return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed overload'}})
            response=fixed_model(payload['messages'])
            return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
        with Anthropic(api_key='placeholder',max_retries=0,timeout=20,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            with contextlib.redirect_stdout(io.StringIO()):out,final,sent,jobs=run(root,allowed,send_override=lambda req:_s11.sdk_send(client,req),after_read=release)
        assert out['status']=='answered'
        assert len(requests)==(4 if allowed else 2)
        assert (root/'count').exists()==allowed
        if allowed:
            assert (root/'count').read_text()=='x' and requests[-1]==requests[-2]
            assert jobs['step_1']['result']['output']=='42'
        print('PASS SDK',allowed,len(requests),'simulated HTTP; direct process once or denied')
