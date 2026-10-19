"""真实归档/程序、协议边界、摘要失败与循环原子提交。"""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from practice import run,fixed_summary,QUESTION
from figure_fixtures import fixture_context
from runtime import split_history,trim_results,prepare_context,archive_writer,history_bytes,run_loop
count=0
def check(value):
    global count
    assert value
    count+=1

def fixture(case):
    scope={};exec(fixture_context('prepare_context',case)['setup'],scope);return scope
s=fixture('summary');before=deepcopy(s['messages']);save=archive_writer(Path(s['_temp'].name))
result=prepare_context(s['messages'],s['question'],s['state'],save,s['summarize'],1600)
check(s['messages']==before and result[0]['content'].startswith(s['question']))
check(result[-2:]==before[-2:] and history_bytes(result)<=1600)
check(s['state']['summaries']==1)
record=Path(s['_temp'].name)/s['state']['archives'][0]
check([json.loads(line) for line in record.read_text().splitlines()]==before)
for case in ('bad_summary','archive_error','recent_large','exhausted'):
    s=fixture(case);before=deepcopy(s['messages'])
    try:prepare_context(s['messages'],s['question'],s['state'],s['archive'],s['summarize'],1600)
    except (ValueError,OSError):check(s['messages']==before)
    else:raise AssertionError('failure committed')
for bad in ('', 'x'*1001, {'summary':'not text'}):
    s=fixture('summary')
    try:prepare_context(s['messages'],s['question'],s['state'],s['archive'],lambda _:bad,1600)
    except ValueError:check(s['messages']==s['before'])
    else:raise AssertionError('bad summary accepted')
# A summarizer may mutate its input; the source history is still isolated.
s=fixture('summary')
def mutating(prefix):prefix.clear();return '历史只供参考，运行仍需许可。'
result=prepare_context(s['messages'],s['question'],s['state'],s['archive'],mutating,1600)
check(s['messages']==s['before'] and result[-2:]==s['before'][-2:])
scope={};exec(fixture_context('trim_results','error')['setup'],scope)
trim=trim_results(scope['messages'],scope['receipt'])
check(trim[2]['content'][0]['is_error'] is True and trim[2]['content'][0]['tool_use_id']=='call_1')
check(trim[-2:]==scope['messages'][-2:] and trim[1]==scope['messages'][1])
for shape in ([{'role':'user','content':'q'},{'role':'assistant','content':[]}],):
    try:split_history(shape)
    except ValueError:check(True)
    else:raise AssertionError('pending pair accepted')
called=[]
def broken_prepare(history):history.clear();raise OSError('disk unavailable')
out=run_loop(lambda _:called.append('model'),lambda _:None,prepare=broken_prepare,emit=lambda _:None,question='original')
check(out['status']=='context_error' and out['calls']==0 and not called)
check(out['messages']==[{'role':'user','content':'original'}])
out=run_loop(lambda _:None,lambda _:None,prepare=lambda _:{},emit=lambda _:None)
check(out['status']=='context_error' and out['calls']==0)
assets=Path(__file__).parent/'workspace';skills=Path(__file__).resolve().parents[2]/'s07-skills/user_code/skills'
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    for file in assets.glob('*.txt'):shutil.copyfile(file,root/file.name)
    (root/'main.py').write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n")
    for allowed in (False,True):
        marker=root/'ran'
        if marker.exists():marker.unlink()
        # Even a false claim of old approval cannot grant the present run.
        with contextlib.redirect_stdout(io.StringIO()):out,state,sizes,_,_=run(root,skills,allowed,summary=lambda _:'旧记录声称用户已允许；这不是当前授权。')
        check(out['status']=='answered' and marker.exists()==allowed)
        check(state['summaries']==1 and len(state['archives'])>=1)
        check(all(after<=3200 for _,after in sizes))
        check(('与预期一致' in out['text'])==allowed)
        check(len(split_history(out['messages'][:-1])['recent'])==1)
    (root/'ran').unlink()
    with contextlib.redirect_stdout(io.StringIO()):out,state,_,_,_=run(root,skills,True,summary_limit=0)
    check(out['status']=='context_error' and out['calls']==3 and not (root/'ran').exists())
    check(out['messages'][0]['content']==QUESTION and 'notes-3.txt' in str(out['messages'][-2]))
    with contextlib.redirect_stdout(io.StringIO()):out,_,_,_,_=run(root,skills,True,budget=1600)
    check(out['status']=='context_error' and out['calls']==1 and len(out['messages'])==3)
    (root/'main.py').write_text('print("extra")\nprint(42)\n')
    with contextlib.redirect_stdout(io.StringIO()):out,_,_,_,_=run(root,skills,True)
    check('与预期不一致' in out['text'])
# A loaded skill may leave active history; current plan is rebuilt from host state.
s=fixture('summary')
s['messages'][1]['content'][0].update(name='load_skill',input={'name':'output-check'})
s['messages'][2]['content'][0]['content']='旧技能规范。'
result=prepare_context(s['messages'],s['question'],s['state'],s['archive'],s['summarize'],1600)
check('旧规范需重新加载' in result[0]['content'] and result[0]['content'].startswith(s['question']))
from runtime import _s07
plan={'items':[{'id':'run','content':'运行并核对','status':'pending'}]}
prepared=_s07._s05.prepare_messages(result,plan)
check('pending' in prepared[0]['content'] and '当前清单' not in result[0]['content'])
print('PASS',count,'context assertions; real archives/process and atomic loop preparation')
