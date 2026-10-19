"""固定SDK模拟HTTP，验证数组schema、工具ID与当前清单输入；不访问模型。"""
import json
import sys
import tempfile
from pathlib import Path
import httpx2 as httpx
from anthropic import Anthropic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION,ask_claude,build_tools,execute_with_plan,prepare_messages,run_loop
from practice import scripted_model
for allowed in (False,True):
 requests=[];state={'items':[]}
 def handle(request):
  body=json.loads(request.content);requests.append(body)
  assert body['messages'][0]['content'].startswith(QUESTION)
  assert body['messages'][0]['content'].count('宿主提供的当前清单')==1
  definition=next(t for t in body['tools'] if t['name']=='todo_write')
  assert definition['input_schema']['properties']['items']['type']=='array'
  response=scripted_model(body['messages'])
  return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
 with tempfile.TemporaryDirectory() as directory:
  root=Path(directory);(root/'main.py').write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n");(root/'expected.txt').write_text('42\n')
  tools=build_tools(root,state)
  with Anthropic(api_key='teaching-placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
   outcome=run_loop(lambda m:ask_claude(client,'teaching-model',prepare_messages(m,state),tools),lambda c:execute_with_plan(c,tools,lambda *_:allowed,{})['result'],max_calls=12,emit=lambda _:None,question=QUESTION)
  assert outcome['status']=='answered' and len(requests)==8
  assert (root/'ran').exists()==allowed
  assert state['items'][-1]['status']==('completed' if allowed else 'pending')
  run=requests[6]['messages'][-1]['content'][0]
  assert run['tool_use_id']=='step_6' and run['is_error']==(not allowed)
  assert all(m['content']==QUESTION for m in outcome['messages'][:1])
 print('PASS SDK 8 simulated HTTP requests, allowed=',allowed,'current plan and actual execution agree')
