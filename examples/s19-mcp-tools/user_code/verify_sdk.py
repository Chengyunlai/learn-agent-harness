"""Anthropic模拟HTTP + 官方MCP真实stdio；工具反馈后的529不重发外部调用。"""
import asyncio
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import demo,fixed_model
from runtime import _s11
for allowed in (True,False):
    attempts=[];failed=False
    def handle(request):
        global failed
        body=json.loads(request.content);attempts.append(body)
        results=[b for m in body['messages'] if isinstance(m['content'],list) for b in m['content'] if b.get('type')=='tool_result']
        if len(results)>=2 and not failed:
            failed=True
            return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
        return httpx.Response(200,json={'id':'msg_fixture','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(body['messages'])})
    with tempfile.TemporaryDirectory() as d,Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        result=asyncio.run(demo(Path(d),allowed,send_override=lambda req:_s11.sdk_send(client,req)))
        assert failed and len(attempts)==(5 if allowed else 4)
        assert len([e for e in result['mcp_events'] if e['event']=='tools/call'])==(1 if allowed else 0)
        assert attempts[0]['tools']==result['requests'][0]['tools']
        assert any(t['name']=='mcp__docs__search_docs' for t in attempts[1]['tools'])
    print('PASS Anthropic simulated HTTP',len(attempts),'real MCP calls',1 if allowed else 0,'; no online model')
