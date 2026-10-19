"""固定SDK模拟HTTP：注册表、system与tools定义一致，本地复用不省略模型请求。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import run,parent_model,child_model
from runtime import _s07,_s09
MEMORY={'name':'report-format','description':'先结论后证据','keywords':['核对'],'body':'每次报告先给结论，再给当前执行证据。','source':'用户明确要求'}
for mode in ('allow','deny','readonly'):
    requests=[];parents=[];children=[]
    def handle(request):
        body=json.loads(request.content);requests.append(body)
        assert 'cache_control' not in body
        if body['system']==_s07._s06.CHILD_SYSTEM:
            children.append(body);assert MEMORY['body'] not in str(body)
            response=child_model(body['messages'],{})
        else:
            parents.append(body);names={tool['name'] for tool in body['tools']}
            assert ('run_main' in names)==(mode!='readonly')
            assert ('run_main：' in body['system'])==(mode!='readonly')
            if mode=='readonly':assert '本次没有run_main' in body['system']
            assert '## skills' in body['system'] and '## memory' in body['system']
            assert MEMORY['body'] not in body['system'] and MEMORY['body'] in body['messages'][0]['content']
            response=parent_model(body['messages'],{name:{} for name in names},body['system'])
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
    with tempfile.TemporaryDirectory() as name:
        root=Path(name);memory=root/'.memory';_s09.save_memory(memory,MEMORY,True)
        (root/'main.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\nprint(42)\n");(root/'expected.txt').write_text('42\n')
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            with contextlib.redirect_stdout(io.StringIO()):
                out,prompts,_,compact=run(root,memory,readonly=mode=='readonly',allowed=mode=='allow',
                    parent=lambda h,t,s:_s07.ask_claude(client,'teaching-model',h,t,s),
                    child=lambda h,t:_s07._s06.ask_claude(client,'teaching-model',h,t,child=True))
        assert out['status']=='answered' and len(children)==3
        assert len(parents)==(4 if mode=='readonly' else 5)
        assert len(requests)==len(parents)+len(children)
        assert [p['reused'] for p in prompts]==[False]+[True]*(len(parents)-1)
        assert (root/'ran').exists()==(mode=='allow')
        assert compact['summaries']==0 and '[项目记忆' not in str(out['messages'])
    print('PASS SDK',mode,':',len(requests),'HTTP calls despite local reuse; system/tools and permission agree')
