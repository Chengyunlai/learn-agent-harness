"""Anthropic1.13.0真实序列化/类型化异常；HTTP全模拟，程序真实执行。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import run
from runtime import sdk_send,_s10
for mode in ('transient','truncated','fatal','long_wait','transport'):
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);(root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n");(root/'expected.txt').write_text('42\n')
  requests=[];failed=False
  def handle(request):
   global failed
   body=json.loads(request.content);requests.append(body)
   after_run=any(m['role']=='user' and isinstance(m['content'],list) and any(str(b.get('content','')).startswith('exit_code=') for b in m['content']) for m in body['messages'])
   if after_run and not failed:
    failed=True
    if mode=='transport':raise httpx.ConnectError('fixed connection failure',request=request)
    if mode in ('transient','fatal','long_wait'):
     status=401 if mode=='fatal' else 429
     return httpx.Response(status,headers={'retry-after':'9' if mode=='long_wait' else '0.5'},json={'type':'error','error':{'type':'authentication_error' if status==401 else 'rate_limit_error','message':'fixed failure'}})
    response={'stop_reason':'max_tokens','content':[{'type':'tool_use','id':'partial','name':'run_main','input':{}}]}
   else:response=_s10.parent_model(body['messages'],{t['name']:{} for t in body['tools']},body['system'])
   return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
  with Anthropic(api_key='placeholder',max_retries=0,timeout=20,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
   with contextlib.redirect_stdout(io.StringIO()):out,state,sent,waits=run(root,allowed=True,send_override=lambda req:sdk_send(client,req))
  assert (root/'count').read_text()=='x'
  assert out['status']==('model_error' if mode in ('fatal','long_wait') else 'answered')
  assert len(requests)==(5 if mode in ('fatal','long_wait') else 6)
  assert 'partial' not in str(out['messages'])
  if mode=='truncated':assert requests[-1]['max_tokens']==2048 and requests[-2]['messages']==requests[-1]['messages']
  if mode=='transient':assert waits==[.5] and requests[-2]==requests[-1]
  assert len(requests)==20-state['remaining']
  print('PASS SDK',mode,len(requests),'parent HTTP attempts; process exactly once, SDK retries disabled')
# 400与413是不同的请求问题，均不解析错误文本自动删历史。
for status in (400,413):
 def invalid(request):return httpx.Response(status,json={'type':'error','error':{'type':'invalid_request_error' if status==400 else 'request_too_large','message':'prompt is too long: fixed fixture'}})
 with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(invalid))) as client:
  result=sdk_send(client,{'model':'teaching-model','messages':[{'role':'user','content':'q'}],'max_tokens':1024})
 assert result['failure']['status']==status
print('PASS SDK 400/413 retain typed status without text-based context guessing')
