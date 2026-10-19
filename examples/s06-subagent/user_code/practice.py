"""同步只读子任务；默认离线模型替身，文件与获准后的进程真实执行。"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION, _s05, ask_claude, build_tools, execute_with_subagent, run_loop


def use(name,arguments,index):
    return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':f'step_{index}','name':name,'input':arguments}]}


def answer(text):
    return {'stop_reason':'end_turn','content':[{'type':'text','text':text}]}


def child_model(messages, tools):
    index=sum(m['role']=='assistant' for m in messages)
    if index==0:return use('read_file',{'path':'main.py'},1)
    if index==1:return use('read_file',{'path':'expected.txt'},2)
    # 固定案例替身只识别这段源码，不能充当通用Python分析器。
    source=messages[2]['content'][0]
    expected=messages[4]['content'][0]
    if source['is_error'] or expected['is_error']:return answer('证据不足：文件读取失败。')
    if source['content'].strip()!='print(6 * 7)':return answer('固定教学替身不分析这段源码；尚未运行。')
    return answer('源码推导输出42；expected.txt='+expected['content'].strip()+'。尚未运行。')


def parent_model(messages):
    index=sum(m['role']=='assistant' for m in messages)
    if index==0:return use('task',{'task':'读取 main.py 和 expected.txt，给出源码推导的输出与预期；不要运行。'},1)
    if index==1:
        result=messages[-1]['content'][0]
        if result['is_error']:return answer('子任务未完成：'+result['content'])
        return use('read_file',{'path':'expected.txt'},2)
    if index==2:return use('run_main',{},3)
    actual=messages[-1]['content'][0]
    expected=messages[4]['content'][0]
    if actual['is_error'] or expected['is_error']:return answer(actual['content'] if actual['is_error'] else expected['content'])
    matches=actual['content'].partition('\n')[2].strip()==expected['content'].strip()
    return answer(actual['content']+('\n与预期一致。' if matches else '\n与预期不一致。'))


def run(workspace, allowed=False, child_calls=4, parent_calls=4, ask_child=child_model, ask_parent=parent_model, emit=print):
    state={'items':[]};traces=[]
    tools=build_tools(workspace,state,ask_child,child_calls,traces)
    def execute(call):
        return execute_with_subagent(call,tools,lambda *_:allowed,{})['result']
    outcome=run_loop(lambda m:ask_parent(_s05.prepare_messages(m,state)),execute,
        max_calls=parent_calls,emit=emit,question=QUESTION)
    return outcome,traces,state


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision',choices=['ask','allow','deny'],default='ask')
    parser.add_argument('--child-calls',type=int,default=4)
    parser.add_argument('--max-calls',type=int,default=4)
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not 1<=args.child_calls<=8 or args.max_calls<1:parser.error('预算无效')
    state={'items':[]};traces=[]
    child=child_model;parent=parent_model
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):parser.error('--live需要API_KEY与MODEL')
        from anthropic import Anthropic
        client=Anthropic(timeout=20,max_retries=0)
        child=lambda m,t:ask_claude(client,os.environ['ANTHROPIC_MODEL'],m,t,child=True)
        parent=lambda m:ask_claude(client,os.environ['ANTHROPIC_MODEL'],m,tools)
    tools=build_tools(args.workspace.resolve(),state,child,args.child_calls,traces)
    def approve(call,reason):
        if args.decision!='ask':return args.decision=='allow'
        if not sys.stdin.isatty():return False
        try:return input(reason+' [y/N] ').strip().lower()=='y'
        except EOFError:return False
    print(('在线模型' if args.live else '离线模型替身')+'；同步子任务，真实文件和获准后的进程')
    outcome=run_loop(lambda m:parent(_s05.prepare_messages(m,state)),
        lambda c:execute_with_subagent(c,tools,approve,{})['result'],
        max_calls=args.max_calls,question=QUESTION)
    print('父循环停止：',outcome['status']);print(outcome['text'])
    print('子循环停止：',[x['status'] for x in traces])
    return 0 if outcome['status']=='answered' else 1


if __name__=='__main__':raise SystemExit(main())
