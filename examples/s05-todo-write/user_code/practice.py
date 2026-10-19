"""TodoWrite离线入口；计划更新不执行程序，实际工具继续经过权限和hooks。"""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION, _s04, ask_claude, build_tools, execute_with_plan, prepare_messages, run_loop

def build_hooks(entries, maintenance=False):
    def record_before(payload): _s04.audit_event('before',payload,entries)
    def record_after(payload): _s04.audit_event('after',payload,entries)
    def check(payload):
        if maintenance and payload['call']['name']=='run_main':return '维护期间暂停运行。'
    return {'before':[record_before,check],'after':[record_after]}


def terminal_approval(call,reason):
    print(f"等待允许：{call['id']} · {call['name']} · {call['input']}\n{reason}")
    if not sys.stdin.isatty():return False
    try:return input('允许这一次？[y/N] ').strip().lower()=='y'
    except EOFError:return False


def plan(statuses):
    return [{'id':str(i+1),'content':text,'status':status} for i,(text,status) in enumerate(zip(
        ['读取源码','读取预期输出','运行并核对'],statuses))]


def scripted_model(messages):
    index=sum(m['role']=='assistant' for m in messages)
    name,arguments='todo_write',{}
    if index==0:arguments={'items':plan(['in_progress','pending','pending'])}
    elif index==1:name,arguments='read_file',{'path':'main.py'}
    elif index==2:arguments={'items':plan(['completed','in_progress','pending'])}
    elif index==3:name,arguments='read_file',{'path':'expected.txt'}
    elif index==4:arguments={'items':plan(['completed','completed','in_progress'])}
    elif index==5:name,arguments='run_main',{}
    elif index==6:
        run=messages[-1]['content'][0]
        arguments={'items':plan(['completed','completed','pending' if run['is_error'] else 'completed'])}
    else:
        results=[b for m in messages if m['role']=='user' and isinstance(m['content'],list) for b in m['content']]
        run=next(r for r in results if r['tool_use_id']=='step_6')
        expected=next(r for r in results if r['tool_use_id']=='step_4')['content'].strip()
        text=run['content'] if run['is_error'] else run['content']+('\n与预期一致。' if run['content'].splitlines()[-1]==expected else '\n与预期不一致。')
        return {'stop_reason':'end_turn','content':[{'type':'text','text':text}]}
    return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':f'step_{index+1}','name':name,'input':arguments}]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision',choices=['ask','allow','deny'],default='ask')
    parser.add_argument('--maintenance',action='store_true')
    parser.add_argument('--max-calls',type=int,default=12)
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if args.max_calls<1:parser.error('--max-calls 必须至少为1')
    state={'items':[]}; entries=[]; warnings=[]; tools=build_tools(args.workspace.resolve(),state)
    hooks=build_hooks(entries,maintenance=args.maintenance)
    answers=iter([args.decision=='allow'])
    def approve(call,reason):
        return terminal_approval(call,reason) if args.decision=='ask' else next(answers,False)
    def execute(call):
        report=execute_with_plan(call,tools,approve,hooks)
        warnings.extend(report['warnings']);return report['result']
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):
            parser.error('--live需要ANTHROPIC_API_KEY和ANTHROPIC_MODEL')
        from anthropic import Anthropic
        client=Anthropic(timeout=20.0,max_retries=0)
        model=lambda m:ask_claude(client,os.environ['ANTHROPIC_MODEL'],m,tools)
    else:model=scripted_model
    print(('在线模型' if args.live else '离线模型替身')+'；真实文件与进程，清单/审计保存在内存')
    outcome=run_loop(lambda m:model(prepare_messages(m,state)),execute,args.max_calls,question=QUESTION)
    print('停止状态：'+outcome['status']);print(outcome['text'])
    print('当前清单：',state['items'])
    for warning in warnings:print('宿主警告：',warning)
    return 0 if outcome['status']=='answered' else 1


if __name__=='__main__':raise SystemExit(main())
