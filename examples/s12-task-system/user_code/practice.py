"""跨进程保存任务进度；固定模型/真实文件与许可/原唯一循环。"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import create_task,claim_task,complete_task,load_board,ready_ids,get_task,build_task_tools,execute_task_call,_s11,_s10,_s07,run_loop


def initialize(directory):
    create_task(directory,'check','检查文件','读取main.py与expected.txt，保存调查结论。',[])
    create_task(directory,'run','运行并核对','重新读取预期，取得本次许可后运行，核对完整输出。',['check'])
    create_task(directory,'report','报告已存结论','引用run任务保存的结果，标明是先前运行证据。',['run'])


def fixed_model(messages,task_id):
    number=sum(m['role']=='assistant' for m in messages)
    last=messages[-1]
    if last['role']=='user' and isinstance(last['content'],list) and last['content'][0]['is_error']:
        return _s10.answer('本次未完成任务：'+last['content'][0]['content'])
    if number==0:return _s10.use('task_claim',{'task_id':task_id},1)
    if task_id=='check':
        if number<=2:return _s10.use('read_file',{'path':'main.py' if number==1 else 'expected.txt'},number+1)
        if number==3:return _s10.use('task_complete',{'task_id':task_id,'result':'已读取源码与预期；尚未运行程序。'},4)
    elif task_id=='run':
        if number==1:return _s10.use('read_file',{'path':'expected.txt'},2)
        if number==2:return _s10.use('run_main',{},3)
        if number==3:
            expected=messages[-3]['content'][0]['content'].strip()
            actual=last['content'][0]['content'];first,_,output=actual.partition('\n')
            if first!='exit_code=0' or output.strip()!=expected:return _s10.answer('运行结果与预期不一致，保留进行中任务供检查。')
            return _s10.use('task_complete',{'task_id':task_id,'result':'本次获准执行，'+actual+'；与当前预期一致。'},4)
    elif task_id=='report':
        if number==1:return _s10.use('task_get',{'task_id':'run'},2)
        if number==2:
            saved=json.loads(last['content'][0]['content'])['result']
            return _s10.use('task_complete',{'task_id':task_id,'result':'引用先前run任务记录：'+saved+' 本阶段没有重新运行程序。'},3)
    return _s10.answer('当前任务已提交完成；下游可开始，不会自动执行。')


def work(workspace,directory,task_id,owner='worker-a',allowed=False,send_override=None):
    state={'items':[]};registry=_s07.scan_skills(Path(__file__).resolve().parents[2]/'s07-skills/user_code/skills')
    tools=_s07.build_tools(workspace,state,_s10.child_model,registry)
    task_tools=build_task_tools(directory,owner);tools.update(task_tools)
    cache={};recovery={'remaining':20,'waited':0.,'events':[]};requests=[]
    compact={'archives':[],'summaries':0,'max_summaries':2}
    question='继续持久任务'+task_id+'；先认领，再按描述取得证据，不把旧状态当成本次执行。'
    def ask(history):
        prompt=_s10.get_system_prompt(_s10.collect_context(workspace,tools,registry,[]),cache)
        prepared=_s07._s05.prepare_messages(history,state)
        request={'model':'teaching-model','system':prompt['system'],'tools':_s07._s05.tool_definitions(tools),'messages':prepared,'max_tokens':1024}
        def send(payload):requests.append(payload);return send_override(payload) if send_override else fixed_model(payload['messages'],task_id)
        return _s11.request_with_recovery(send,request,recovery,pause=lambda _:None,random_unit=lambda:0)
    out=run_loop(ask,lambda call:execute_task_call(call,tools,set(task_tools),allowed),question=question,max_calls=6,
        prepare=lambda h:_s10._s08.prepare_context(h,question,compact,_s10._s08.archive_writer(workspace/'.context'),lambda _:'继续当前任务，完成标记与执行证据分别核对。'))
    return out,recovery,requests


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['init','show','work','complete'])
    parser.add_argument('--store',type=Path,default=Path(__file__).parent/'workspace/.tasks')
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--task',default='check');parser.add_argument('--owner',default='worker-a')
    parser.add_argument('--decision',choices=['allow','deny'],default='deny');parser.add_argument('--result',default='')
    args=parser.parse_args()
    try:
        if args.command=='init':initialize(args.store);print('已创建check → run → report；可开始：',ready_ids(load_board(args.store)))
        elif args.command=='show':print(json.dumps(load_board(args.store),ensure_ascii=False,indent=2));print('可开始：',ready_ids(load_board(args.store)))
        elif args.command=='complete':print(complete_task(args.store,args.task,args.owner,args.result))
        else:
            print('固定模型；真实持久文件与获准进程。只恢复任务状态，不恢复旧对话或自动重跑进行中任务。')
            out,recovery,_=work(args.workspace.resolve(),args.store,args.task,args.owner,args.decision=='allow')
            print('停止状态：',out['status']);print(out['text']);print('可开始：',ready_ids(load_board(args.store)))
            return 0 if out['status']=='answered' and get_task(args.store,args.task)['status']=='completed' else 1
    except (ValueError,OSError) as error:print('任务操作失败：',error);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
