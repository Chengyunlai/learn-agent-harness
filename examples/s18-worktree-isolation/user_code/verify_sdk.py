"""Anthropic1.13.0模拟HTTP，真实Git/文件/进程；不调用在线模型。"""
import json
import tempfile
from pathlib import Path
from threading import Lock
from unittest.mock import patch
import httpx2 as httpx
from anthropic import Anthropic
from practice import demo,fixed_model
from runtime import _s11
for allowed in (True,False):
    requests=[];guard=Lock();failed=False;writes=[];original=Path.write_text
    def write(path,*args,**kwargs):
        if path.name=='main.py' and path.parent.name in ('alpha','beta'):writes.append(str(path))
        return original(path,*args,**kwargs)
    def handle(request):
        global failed
        body=json.loads(request.content);actor=body['messages'][0]['content'].split(':',1)[0]
        has_result=any(isinstance(m['content'],list) and any(b.get('type')=='tool_result' for b in m['content']) for m in body['messages'])
        with guard:
            requests.append(body);retry=has_result and not failed
            if retry:failed=True
        if retry:return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
        return httpx.Response(200,json={'id':'msg_fixture','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(body['messages'],actor)})
    with tempfile.TemporaryDirectory() as d,Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client,patch.object(Path,'write_text',write):
        result=demo(Path(d),allowed,lambda req:_s11.sdk_send(client,req))
        assert failed and len(requests)==7 and len(result['traces'])==6
        assert len(writes)==(2 if allowed else 0)
        assert all(x['status']==('completed' if allowed else 'needs_attention') for x in result['reports'].values())
        assert result['main']=='print(0)\n'
    print('PASS SDK 7 simulated HTTP; two own cwd; no duplicate write after529; allowed:',allowed)
