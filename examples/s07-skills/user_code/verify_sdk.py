"""固定SDK模拟HTTP：目录在system，正文只在load结果后进入父messages。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import parent_model,child_model,BASE
from runtime import QUESTION,_s06,_s05,scan_skills,build_system,build_tools,execute_with_skills,ask_claude,run_loop
for allowed in (False,True):
    requests=[]
    registry=scan_skills(Path(__file__).parent/'skills');system=build_system(registry,BASE)
    body=Path(registry['output-check']['path']).read_text()
    sql_body='此任务没有SQL；这段正文不应出现在模型请求中。'
    def handle(request):
        payload=json.loads(request.content);requests.append(payload)
        child=payload['system']==_s06.CHILD_SYSTEM
        assert sql_body not in json.dumps(payload,ensure_ascii=False)
        if child:
            assert {t['name'] for t in payload['tools']}=={'read_file'}
            assert '可用技能' not in payload['system']
            response=child_model(payload['messages'],{})
        else:
            assert body not in payload['system'] and 'output-check' in payload['system'] and 'sql-style' in payload['system']
            if len(payload['messages'])==1:assert body not in json.dumps(payload,ensure_ascii=False)
            else:
                load=payload['messages'][2]['content'][0]
                assert load['tool_use_id']=='step_1' and load['content']==body
            definition=next(t for t in payload['tools'] if t['name']=='load_skill')
            assert definition['input_schema']['properties']['name']['type']=='string'
            response=parent_model(payload['messages'])
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);(root/'main.py').write_text('print(6 * 7)\n');(root/'expected.txt').write_text('42\n');state={'items':[]}
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            child=lambda m,t:_s06.ask_claude(client,'teaching-model',m,t,child=True)
            tools=build_tools(root,state,child,registry)
            with contextlib.redirect_stdout(io.StringIO()):
                out=run_loop(lambda m:ask_claude(client,'teaching-model',_s05.prepare_messages(m,state),tools,system),lambda c:execute_with_skills(c,tools,lambda *_:allowed,{})['result'],max_calls=6,question=QUESTION)
        assert out['status']=='answered' and len(requests)==8
        assert ('已执行' in out['text'])==allowed
    print('PASS 8 SDK mock HTTP requests; catalog/body boundaries; allowed=',allowed)
