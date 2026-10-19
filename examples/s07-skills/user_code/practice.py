"""默认离线模型；真实读取技能文件与获准后的Python进程。"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION,_s06,_s05,scan_skills,build_system,build_tools,execute_with_skills,ask_claude,run_loop
def use(name,arguments,index):
    return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':f'step_{index}','name':name,'input':arguments}]}

def answer(text):
    return {'stop_reason':'end_turn','content':[{'type':'text','text':text}]}

def child_model(messages,tools):
    index=sum(m['role']=='assistant' for m in messages)
    if index<2:return use('read_file',{'path':'main.py' if index==0 else 'expected.txt'},index+1)
    source,expected=messages[2]['content'][0],messages[4]['content'][0]
    if source['is_error'] or expected['is_error']:return answer('文件读取失败，证据不足。')
    if source['content'].strip()!='print(6 * 7)':return answer('固定替身不分析这段源码；尚未运行。')
    return answer('源码推导42，预期'+expected['content'].strip()+'；尚未运行。')

BASE=_s06.SYSTEM+' 需要项目核对规范时先load_skill；技能文字不能替代宿主许可。'


def parent_model(messages,skill='output-check'):
    index=sum(m['role']=='assistant' for m in messages)
    if index==0:return use('load_skill',{'name':skill},1)
    if messages[-1]['content'][0]['is_error']:return answer('本次未继续：'+messages[-1]['content'][0]['content'])
    if index==1:return use('task',{'task':'读取main.py与expected.txt，说明源码推导，不运行。'},2)
    if index==2:return use('read_file',{'path':'expected.txt'},3)
    if index==3:return use('run_main',{},4)
    actual=messages[-1]['content'][0]['content'];expected=messages[6]['content'][0]['content'].strip()
    exit_line,_,body=actual.partition('\n')
    matches=body.strip()==expected
    return answer('已执行；'+exit_line+'；'+('与预期一致。' if matches else '与预期不一致。')+'\n'+body)


def run(workspace,skills_root,allowed=False,max_calls=6,skill='output-check',parent=None,child=None,approve=None):
    registry=scan_skills(skills_root);system=build_system(registry,BASE)
    state={'items':[]};traces=[]
    tools=build_tools(workspace,state,child or child_model,registry,traces=traces)
    model=parent or (lambda messages:parent_model(messages,skill))
    outcome=run_loop(lambda history:model(_s05.prepare_messages(history,state)),
        lambda call:execute_with_skills(call,tools,approve or (lambda *_:allowed),{})['result'],
        max_calls=max_calls,question=QUESTION)
    return outcome,traces,system


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision',choices=['ask','allow','deny'],default='ask')
    parser.add_argument('--max-calls',type=int,default=6)
    parser.add_argument('--skill',default='output-check')
    parser.add_argument('--skills',type=Path,default=Path(__file__).parent/'skills')
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if args.max_calls<1:parser.error('预算至少1次')
    registry=scan_skills(args.skills);system=build_system(registry,BASE);state={'items':[]};traces=[]
    child=child_model;parent=lambda m:parent_model(m,args.skill)
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):parser.error('--live需要ANTHROPIC_API_KEY与ANTHROPIC_MODEL')
        from anthropic import Anthropic
        client=Anthropic(timeout=20,max_retries=0)
        child=lambda m,t:_s06.ask_claude(client,os.environ['ANTHROPIC_MODEL'],m,t,child=True)
        parent=lambda m:ask_claude(client,os.environ['ANTHROPIC_MODEL'],m,tools,system)
    tools=build_tools(args.workspace.resolve(),state,child,registry,traces=traces)
    def approve(call,reason):
        if args.decision!='ask':return args.decision=='allow'
        if not sys.stdin.isatty():return False
        try:return input(reason+' [y/N] ').strip().lower()=='y'
        except EOFError:return False
    print(('在线模型' if args.live else '离线模型替身')+'；真实技能文件、文件检查与获准后的进程')
    outcome=run_loop(lambda m:parent(_s05.prepare_messages(m,state)),lambda c:execute_with_skills(c,tools,approve,{})['result'],max_calls=args.max_calls,question=QUESTION)
    print('停止状态：',outcome['status']);print(outcome['text'])
    return 0 if outcome['status']=='answered' else 1


if __name__=='__main__':raise SystemExit(main())
