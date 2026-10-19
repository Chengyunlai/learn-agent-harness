"""Anthropic SDK +模拟HTTP，父子system/tools/messages分开；不访问模型。"""
import json
import tempfile
from pathlib import Path
import httpx2 as httpx
from anthropic import Anthropic
from practice import run,parent_model,child_model
from runtime import ask_claude,CHILD_SYSTEM,SYSTEM,QUESTION
for allowed in (False,True):
    requests=[];registered={}
    def handle(request):
        body=json.loads(request.content);requests.append(body)
        child=body['system']==CHILD_SYSTEM
        if child:
            assert {t['name'] for t in body['tools']}=={'read_file'}
            assert QUESTION not in body['messages'][0]['content']
            response=child_model(body['messages'],{})
        else:
            assert body['system']==SYSTEM
            assert {t['name'] for t in body['tools']}=={'read_file','run_main','todo_write','task'}
            response=parent_model(body['messages'])
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);(root/'main.py').write_text('print(6 * 7)\n');(root/'expected.txt').write_text('42\n')
        from runtime import build_tools,execute_with_subagent,run_loop,_s05
        state={'items':[]};traces=[]
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            child=lambda m,t:ask_claude(client,'teaching-model',m,t,child=True)
            tools=build_tools(root,state,child,traces=traces)
            outcome=run_loop(lambda m:ask_claude(client,'teaching-model',_s05.prepare_messages(m,state),tools),lambda c:execute_with_subagent(c,tools,lambda *_:allowed,{})['result'],max_calls=4,question=QUESTION,emit=lambda _:None)
        assert outcome['status']=='answered' and len(requests)==7
        assert sum(r['system']==CHILD_SYSTEM for r in requests)==3
        parent_requests=[r for r in requests if r['system']==SYSTEM]
        assert len(parent_requests)==4
        result=parent_requests[1]['messages'][-1]['content'][0]
        assert result['tool_use_id']=='step_1' and 'messages' not in result['content']
        assert ('与预期一致' in outcome['text'])==allowed
    print('PASS 7 SDK simulated requests; allowed=',allowed)
