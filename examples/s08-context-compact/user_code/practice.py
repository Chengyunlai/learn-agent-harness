"""默认离线主/子/摘要模型替身；真实日志、快照与获准后的进程。"""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION,_s07,run_loop,prepare_context,archive_writer,summarize_claude,history_bytes


def use(name,args,number):
    return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':f'step_{number}','name':name,'input':args}]}
def answer(text):
    return {'stop_reason':'end_turn','content':[{'type':'text','text':text}]}
def child_model(history,tools):
    index=sum(m['role']=='assistant' for m in history)
    if index<2:return use('read_file',{'path':'main.py' if index==0 else 'expected.txt'},index+1)
    return answer('已读取两份文件，源码推导仍需实际运行核对。')
def parent_model(messages):
    if len(messages)==1:number=1
    else:number=int(messages[-1]['content'][0]['tool_use_id'].split('_')[-1])+1
    if number>1 and messages[-1]['content'][0]['is_error']:return answer('未继续：'+messages[-1]['content'][0]['content'])
    if number<=4:return use('read_file',{'path':f'notes-{number}.txt'},number)
    if number==5:return use('load_skill',{'name':'output-check'},number)
    if number==6:return use('task',{'task':'读取main.py与expected.txt，只读检查，不声称已经运行。'},number)
    if number==7:return use('read_file',{'path':'expected.txt'},number)
    if number==8:return use('run_main',{},number)
    actual=messages[-1]['content'][0]['content']
    results=[b for m in messages if m['role']=='user' and type(m['content']) is list for b in m['content']]
    expected=next((b['content'] for b in results if b['tool_use_id']=='step_7'),None)
    if expected is None or expected.startswith('[旧正文'):return answer('缺少完整预期，尚不能核对；需要补读。实际结果：\n'+actual)
    matches=actual.partition('\n')[2].strip()==expected.strip()
    return answer('实际结果：\n'+actual+('\n与预期一致。' if matches else '\n与预期不一致。'))
def fixed_summary(prefix):
    return '已检查旧日志；旧正文已归档，不能推断本次结果。继续按当前用户要求查文件、取得运行许可并报告实际反馈。'


def run(workspace,skills,allowed=False,budget=3200,summary_limit=2,summary=None,max_calls=12,parent=None,child=None,approve=None):
    state={'items':[]};compact={'archives':[],'summaries':0,'max_summaries':summary_limit};traces=[];sizes=[]
    registry=_s07.scan_skills(skills);system=_s07.build_system(registry,_s07._s06.SYSTEM)
    tools=_s07.build_tools(workspace,state,child or child_model,registry,traces=traces)
    archive=archive_writer(workspace/'.context')
    def prepare(history):
        candidate=prepare_context(history,QUESTION,compact,archive,summary or fixed_summary,budget)
        sizes.append((history_bytes(history),history_bytes(candidate)))
        return candidate
    out=run_loop(lambda history:(parent or parent_model)(_s07._s05.prepare_messages(history,state)),
        lambda call:_s07.execute_with_skills(call,tools,approve or (lambda *_:allowed),{})['result'],
        max_calls=max_calls,question=QUESTION,prepare=prepare)
    return out,compact,sizes,tools,system


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision',choices=['ask','allow','deny'],default='ask')
    parser.add_argument('--budget',type=int,default=3200)
    parser.add_argument('--summary-limit',type=int,default=2)
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if args.budget<400 or args.summary_limit<0:parser.error('预算无效')
    skills=Path(__file__).resolve().parents[2]/'s07-skills/user_code/skills'
    def approve(call,reason):
        if args.decision!='ask':return args.decision=='allow'
        if not sys.stdin.isatty():return False
        try:return input(reason+' [y/N] ').strip().lower()=='y'
        except EOFError:return False
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):parser.error('--live需要API_KEY与MODEL')
        from anthropic import Anthropic
        client=Anthropic(timeout=20,max_retries=0);model=os.environ['ANTHROPIC_MODEL']
        compact={'archives':[],'summaries':0,'max_summaries':args.summary_limit};state={'items':[]}
        registry=_s07.scan_skills(skills);system=_s07.build_system(registry,_s07._s06.SYSTEM)
        tools=_s07.build_tools(args.workspace,state,lambda h,t:_s07._s06.ask_claude(client,model,h,t,child=True),registry)
        save=archive_writer(args.workspace/'.context')
        out=run_loop(lambda h:_s07.ask_claude(client,model,_s07._s05.prepare_messages(h,state),tools,system),lambda c:_s07.execute_with_skills(c,tools,approve,{})['result'],max_calls=12,question=QUESTION,
            prepare=lambda h:prepare_context(h,QUESTION,compact,save,lambda p:summarize_claude(client,model,p),args.budget))
    else:
        print('离线主/子/摘要模型；真实文件、快照与获准后的进程。')
        out,compact,sizes,_,_=run(args.workspace.resolve(),skills,approve=approve,budget=args.budget,summary_limit=args.summary_limit)
        print('消息字节（整理前→后）：',sizes)
    print('停止状态：',out['status']);print(out['text'])
    print('摘要尝试：',compact['summaries'],'；压缩前快照：',compact['archives'])
    return 0 if out['status']=='answered' else 1


if __name__=='__main__':raise SystemExit(main())
