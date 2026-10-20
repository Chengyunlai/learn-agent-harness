"""SDK1.13.0模拟HTTP；真实并发认领与程序，模型请求恢复不重复工作。"""
import json
from pathlib import Path
import tempfile
import threading
import httpx2 as httpx
from anthropic import Anthropic
from practice import demo,fixed_model
from runtime import _s11,load_inbox
for allowed,expected in [(True,'42'),(False,'42'),(True,'43')]:
 requests=[];failed=False;guard=threading.Lock()
 def handle(request):
  global failed
  body=json.loads(request.content)
  anchor=[m['content'] for m in body['messages'] if isinstance(m['content'],str) and m['content'].startswith('[auto-turn]')][-1]
  actor,task=anchor.split('\n',1)[0].split(' ',1)[1].split(':')
  has_result=any(isinstance(m['content'],list) and any(b.get('type')=='tool_result' for b in m['content']) for m in body['messages'])
  with guard:
   requests.append(body);retry=actor!='lead' and has_result and not failed
   if retry:failed=True
  if retry:return httpx.Response(529,json={'type':'error','error':{'type':'overloaded_error','message':'fixed'}})
  return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**fixed_model(body['messages'],actor,task)})
 with tempfile.TemporaryDirectory() as d,Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
  root=Path(d);work=root/'work';work.mkdir();(work/'expected.txt').write_text(expected);(work/'main.py').write_text("from pathlib import Path\np=Path('count')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
  result=demo(root/'state',work,allowed,lambda actor,task,req:_s11.sdk_send(client,req))
  assert failed and len(requests)==8 and len(result['reports'])==3
  assert len(load_inbox(root/'state/mail','lead',result['team']))==5
  assert (work/'count').exists()==allowed
  if allowed:assert (work/'count').read_text()=='x'
  assert result['board']['tasks']['verify']['status']==('completed' if allowed and expected=='42' else 'in_progress')
  assert all(t['owner'] is not None for t in result['board']['tasks'].values())
  print('PASS SDK 8 simulated HTTP, 3 unique tasks/5 Lead inbox records; allowed/expected:',allowed,expected,'; no online model')
