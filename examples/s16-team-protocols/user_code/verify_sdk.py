"""SDK1.13.0模拟HTTP；计划回复之后注入529，不重复协议消息或真实运行。"""
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import demo,fixed_model
from runtime import _s11,load_inbox
for plan,permission in [(True,True),(False,True),(True,False)]:
    requests=[];failed=False
    def handle(request):
        global failed
        body=json.loads(request.content);requests.append(body)
        anchor=[m['content'] for m in body['messages'] if isinstance(m['content'],str) and m['content'].startswith('[protocol-turn]')][-1]
        actor,phase=anchor.split('\n',1)[0].split(' ',1)[1].split(':')
        if phase=='review' and any(isinstance(m['content'],list) and any(b.get('type')=='tool_result' for b in m['content']) for m in body['messages']) and not failed:
            failed=True;return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(body['messages'],actor,phase,plan)})
    with tempfile.TemporaryDirectory() as d,Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        root=Path(d);work=root/'work';work.mkdir();(work/'expected.txt').write_text('42');(work/'main.py').write_text("from pathlib import Path\np=Path('count')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
        result=demo(root/'mail',work,plan,permission,lambda actor,phase,req:_s11.sdk_send(client,req))
        assert len(requests)==8 and failed
        assert len(load_inbox(root/'mail','lead',result['team']))==2 and len(load_inbox(root/'mail','reader',result['team']))==2
        assert (work/'count').exists()==(plan and permission)
        if (work/'count').exists():assert (work/'count').read_text()=='x'
        assert all('sender' not in str(t.get('input_schema',{})) for req in requests for t in req['tools'])
        print('PASS SDK 8 simulated HTTP, 4 mailbox messages; plan/host:',plan,permission,'; no online model')
