"""普通Messages SDK模拟主/子/摘要三类请求，不使用服务端压缩接口。"""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import httpx2 as httpx
from anthropic import Anthropic
from practice import parent_model,child_model,fixed_summary
from runtime import QUESTION,_s07,run_loop,prepare_context,archive_writer,summarize_claude,history_bytes
for allowed in (False,True):
    requests=[];seen=[]
    def handle(request):
        body=json.loads(request.content);requests.append(body)
        if body['system'].startswith('只整理已知目标'):
            prefix=json.loads(body['messages'][0]['content'])
            assert prefix[0]['role']=='user' and len(prefix)>1
            assert '旧正文已移出' in str(prefix)
            response={'stop_reason':'end_turn','content':[{'type':'text','text':fixed_summary(prefix)}]}
        elif body['system']==_s07._s06.CHILD_SYSTEM:
            response=child_model(body['messages'],{})
            assert {t['name'] for t in body['tools']}=={'read_file'}
        else:
            assert QUESTION in body['messages'][0]['content']
            assert '可用技能（仅目录）' in body['system']
            if '[历史摘要' in body['messages'][0]['content']:seen.append(True)
            response=parent_model(body['messages'])
        return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':10},**response})
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        for file in (Path(__file__).parent/'workspace').glob('*.*'):
            if file.is_file():shutil.copyfile(file,root/file.name)
        state={'items':[]};compact={'archives':[],'summaries':0,'max_summaries':2}
        registry=_s07.scan_skills(Path(__file__).resolve().parents[2]/'s07-skills/user_code/skills')
        system=_s07.build_system(registry,_s07._s06.SYSTEM)
        with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
            tools=_s07.build_tools(root,state,lambda h,t:_s07._s06.ask_claude(client,'teaching-model',h,t,child=True),registry)
            with contextlib.redirect_stdout(io.StringIO()):
                out=run_loop(lambda h:_s07.ask_claude(client,'teaching-model',_s07._s05.prepare_messages(h,state),tools,system),lambda c:_s07.execute_with_skills(c,tools,lambda *_:allowed,{})['result'],max_calls=12,question=QUESTION,
                    prepare=lambda h:prepare_context(h,QUESTION,compact,archive_writer(root/'.context'),lambda p:summarize_claude(client,'teaching-model',p)))
        assert out['status']=='answered' and len(requests)==13 and compact['summaries']==1 and seen
        assert ('与预期一致' in out['text'])==allowed
    print('PASS 13 SDK mock requests; parent/child/summary separated; allowed=',allowed)
# max_tokens is not a complete summary, even if a text block exists.
def truncated(request):
    return httpx.Response(200,json={'id':'msg_demo','type':'message','role':'assistant','model':'teaching-model','stop_reason':'max_tokens','stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':1},'content':[{'type':'text','text':'half'}]})
with Anthropic(api_key='placeholder',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(truncated))) as client:
    try:summarize_claude(client,'teaching-model',[{'role':'user','content':'q'}])
    except ValueError:print('PASS truncated SDK summary rejected')
    else:raise AssertionError('truncated summary accepted')
