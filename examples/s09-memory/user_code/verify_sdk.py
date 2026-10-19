"""固定SDK模拟HTTP；检验记忆正文只进父请求副本，子任务和许可保持独立。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import run, parent_model, child_model
from runtime import save_memory, _s07
candidate=json.loads((Path(__file__).parent/'report-memory.json').read_text())
for allowed in (False,True):
    requests=[];parents=[];children=[]
    def handle(request):
        body=json.loads(request.content);requests.append(body)
        if body['system']==_s07._s06.CHILD_SYSTEM:
            assert candidate['body'] not in str(body)
            children.append(body);response=child_model(body['messages'],{})
        else:
            parents.append(body)
            assert candidate['body'] not in body['system']
            assert 'report-format' in body['system']
            assert body['messages'][0]['content'].count('[项目记忆')==1
            assert candidate['body'] in body['messages'][0]['content']
            assert 'SQL关键字使用大写' not in str(body)
            response=parent_model(body['messages'])
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
    with tempfile.TemporaryDirectory() as name:
        root=Path(name);directory=root/'.memory';save_memory(directory,candidate,True)
        save_memory(directory,{**candidate,'name':'sql-style','keywords':['SQL'],'body':'SQL关键字使用大写。'},True)
        (root/'main.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\nprint(42)\n")
        (root/'expected.txt').write_text('42\n')
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            with contextlib.redirect_stdout(io.StringIO()):
                out,selected,_,compact=run(root,directory,allowed,
                    parent=lambda h,t,s:_s07.ask_claude(client,'teaching-model',h,t,s),
                    child=lambda h,t:_s07._s06.ask_claude(client,'teaching-model',h,t,child=True))
        assert len(requests)==8 and len(parents)==5 and len(children)==3 and compact['summaries']==0
        assert selected==['report-format'] and out['status']=='answered'
        assert (root/'ran').exists()==allowed
        assert ('是否执行：是' in out['text'])==allowed
        assert '[项目记忆' not in str(out['messages'])
    print('PASS 8 SDK mock requests: parent5/child3; related memory, isolated history, allowed=',allowed)
