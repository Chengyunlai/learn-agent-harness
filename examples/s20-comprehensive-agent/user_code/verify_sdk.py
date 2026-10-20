"""Anthropic1.13.0模拟HTTP；MCP真实stdio；529发生在进程结果之后。"""
import asyncio,json,tempfile
from pathlib import Path
import httpx2 as httpx
from anthropic import Anthropic
from practice import seed,real_mcp
from runtime import _s11
for allowed in (True,False):
    attempts=[];failed=[False]
    def send(request,model):
        def handle(raw):
            body=json.loads(raw.content);attempts.append(body)
            if model.index==(4 if allowed else 3) and not failed[0]:
                failed[0]=True;return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}},headers={'retry-after':'0'})
            return httpx.Response(200,json={'id':'msg_fixture','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**model(body)})
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:return _s11.sdk_send(client,request)
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);seed(root);out=asyncio.run(real_mcp(root,allowed,send_override=send))
        assert out['verified']==allowed and failed[0]
        assert len(attempts)==(6 if allowed else 5)
        assert len([e for e in out['mcp_events'] if e['event']=='tools/call'])==(1 if allowed else 0)
        assert len([e for e in out['audit'] if e['event']=='after' and e['tool']=='run_main'])==(1 if allowed else 0)
        assert attempts[-1]==attempts[-2];assert out['closed']==['host-finish'];assert out['protocol']=='2025-11-25'
    print('PASS real MCP, real file/archive/process, simulated HTTP',len(attempts),'allowed',allowed,'no repeated tool; no online model')
