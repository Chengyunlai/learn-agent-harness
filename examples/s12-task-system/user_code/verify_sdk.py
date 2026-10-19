"""固定SDK模拟HTTP；真实任务JSON、真实文件进程，任务工具不重复提交。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import initialize,work,fixed_model
from runtime import _s11,load_board,get_task,ready_ids
for allowed in (True,False):
 with tempfile.TemporaryDirectory() as name:
  root=Path(name);store=root/'.tasks';initialize(store)
  (root/'main.py').write_text("from pathlib import Path\np=Path('count');p.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n");(root/'expected.txt').write_text('42\n')
  requests=[];injected=False
  for task_id in ('check','run','report'):
   def handle(request):
    global injected
    body=json.loads(request.content);requests.append(body)
    tools={t['name']:t for t in body['tools']}
    assert len(tools)==10 and {'task_create','task_list','task_get','task_claim','task_complete'}<=set(tools)
    assert 'owner' not in tools['task_claim']['input_schema']['properties']
    assert 'task_claim' in body['system'] and body['max_tokens']==1024
    last=body['messages'][-1]
    if allowed and task_id=='run' and not injected and last['role']=='user' and isinstance(last['content'],list) and 'unlocked' in last['content'][0]['content']:
     injected=True
     return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed temporary failure'}})
    response=fixed_model(body['messages'],task_id)
    return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
   with Anthropic(api_key='placeholder',max_retries=0,timeout=20,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
    with contextlib.redirect_stdout(io.StringIO()):out,state,sent=work(root,store,task_id,allowed=allowed,send_override=lambda p:_s11.sdk_send(client,p))
   assert out['status']=='answered'
   assert len(sent)==20-state['remaining']
  if allowed:
   assert (root/'count').read_text()=='x' and load_board(store)['revision']==9 and ready_ids(load_board(store))==[]
   assert len(requests)==15 and injected
   assert '先前run任务记录' in get_task(store,'report')['result']
  else:
   assert not (root/'count').exists() and load_board(store)['revision']==6
   assert get_task(store,'run')['status']=='in_progress' and get_task(store,'report')['status']=='pending'
   assert len(requests)==11
  print('PASS SDK', 'allow+529' if allowed else 'deny+blocked',len(requests),'HTTP calls; owner host-bound, task writes and actual execution agree')
