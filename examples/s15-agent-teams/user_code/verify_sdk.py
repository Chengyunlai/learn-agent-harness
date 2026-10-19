"""固定SDK+模拟HTTP；真实双线程、文件与邮箱；模型请求恢复不重复发信。"""
import contextlib
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import demo, fixed_model
from runtime import _s11, load_inbox
with tempfile.TemporaryDirectory() as d, contextlib.ExitStack() as stack:
    root=Path(d);work=root/'work';work.mkdir();(work/'main.py').write_text('print(6*7)');(work/'expected.txt').write_text('42')
    failed=False;requests=[];clients={}
    for actor in ('reader','reviewer','lead'):
        def handle(request, actor=actor):
            global failed
            body=json.loads(request.content);requests.append((actor,body))
            sent=any(isinstance(m['content'],list) and any(b.get('type')=='tool_result' and b.get('tool_use_id')=='reader-1-2' for b in m['content']) for m in body['messages'])
            if actor=='reader' and sent and not failed:
                failed=True;return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
            return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(body['messages'],actor)})
        clients[actor]=stack.enter_context(Anthropic(api_key='placeholder',max_retries=0,timeout=20,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    team,reports,lead,traces=demo(root/'mail',work,lambda actor,req:_s11.sdk_send(clients[actor],req))
    assert all(r['status']=='answered' for r in reports)
    assert len(requests)==10 and len(load_inbox(root/'mail','lead',team))==2 and len(load_inbox(root/'mail','reader',team))==1
    assert all({tool['name'] for tool in req['tools']}=={'read_file','send_message'} for _,req in requests)
    reader=[body for actor,body in requests if actor=='reader']
    assert any(a==b for a,b in zip(reader,reader[1:]))
    assert 'reader-1-1' in str(reader[-1]['messages'])
    print('PASS SDK 10 simulated HTTP, 3 mailbox records, retained reader context; no duplicate send, no online model')
