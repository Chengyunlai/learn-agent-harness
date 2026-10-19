"""固定模型；真实JSONL协议与获准后的Python进程，没有在线模型。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import create_team, run_teammate, open_request, reply_request, consume_responses, prepare_inbox, load_inbox, read_protocol, plan_gate, run_loop, _s07, _s10, _s11
PLAN = '读取expected.txt，再运行main.py并比较本次输出。'


def fixed_model(messages, actor, phase, approve):
    anchor = max(i for i,m in enumerate(messages) if isinstance(m['content'],str) and m['content'].startswith('[protocol-turn]'))
    count = sum(m['role']=='assistant' for m in messages[anchor+1:])
    tool, args = None, {}
    if phase == 'plan' and count == 0:
        tool,args='submit_plan',{'payload':PLAN}
    if phase == 'review' and count == 0:
        notices=[json.loads(m['content'].split(' ',1)[1]) for m in messages if isinstance(m['content'],str) and m['content'].startswith('[team-message] ')]
        request=next(read_protocol(m) for m in notices if read_protocol(m) and read_protocol(m)['type']=='plan_request')
        tool,args='review_plan',{'request_id':request['request_id'],'approve':approve,'feedback':'只允许这份固定计划；执行许可另问宿主。'}
    if phase == 'work':
        if count == 0:tool,args='read_file',{'path':'expected.txt'}
        if count == 1:tool='run_main'
    if tool:
        response=_s10.use(tool,args,count+1);response['content'][0]['id']=f'{actor}-{phase}-{count+1}';return response
    if phase=='work':
        results=[b for m in messages[anchor+1:] if isinstance(m['content'],list) for b in m['content'] if b.get('type')=='tool_result']
        return _s10.answer('本次工具反馈：'+results[-1]['content'])
    return _s10.answer('本轮协议消息已保存；请求方匹配后才推进状态。')


def run_member(previous, actor, phase, state, team, directory, workspace, lock, approve, allowed, plan_id=None, send_override=None, traces=None):
    def submit(payload):return json.dumps(open_request(state,team,directory,actor,'lead','plan',payload,lock))
    def review(request_id, approve, feedback):return json.dumps(reply_request(state,team,directory,request_id,actor,approve,feedback,lock))
    tools = ({'submit_plan': {'description':'提出本次只读与运行计划，不自动执行。','parameters':{'payload':str},'run':submit}} if phase=='plan' else
             {'review_plan': {'description':'由Lead回复计划决定，不代替用户执行许可。','parameters':{'request_id':str,'approve':bool,'feedback':str},'run':review}} if phase=='review' else _s07._s02.build_tools(workspace))
    recovery={'remaining':20,'waited':0.,'events':[]};cache={}
    def prepare(current):
        consume_responses(state,team,directory,actor,lock)
        return prepare_inbox(previous+current,directory,team,actor,lock)[len(previous):]
    def ask(current):
        request={'model':'teaching-model','system':_s10.get_system_prompt(_s10.collect_context(workspace,tools,{},[]),cache)['system']+'\n宿主身份：'+actor,
                 'tools':_s07._s02.tool_definitions(tools),'messages':previous+current,'max_tokens':1024}
        if traces is not None:traces.append({'actor':actor,'phase':phase,'request':deepcopy(request)})
        return _s11.request_with_recovery(send_override or (lambda req:fixed_model(req['messages'],actor,phase,approve)),request,recovery,pause=lambda _:None,random_unit=lambda:0)
    def execute(call):
        guard = (lambda snapshot,registered,*_:_s07._s02.execute_tool(snapshot,registered)) if phase in ('plan','review') else None
        return _s07._s04.execute_hooked(call,tools,lambda *_:allowed,{'before':[plan_gate(state,plan_id,actor,lock)]},guard=guard)['result']
    outcome=run_loop(ask,execute,max_calls=4,emit=lambda _:None,prepare=prepare,question=f'[protocol-turn] {actor}:{phase}\n计划协商与实际执行分别验证。')
    outcome['messages']=previous+outcome['messages'];return outcome


def demo(directory, workspace, approve=True, allowed=False, send_override=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if any(directory.iterdir()):raise ValueError('本课需要空邮箱，不恢复旧会话。')
    state,team,lock,traces={},create_team(),threading.RLock(),[]
    def turn(previous,actor,phase,plan_id=None):
        send=(lambda request:send_override(actor,phase,request)) if send_override else None
        return run_member(previous,actor,phase,state,team,directory,workspace,lock,approve,allowed,plan_id,send,traces)
    first=run_teammate(team,'reader',lambda history:turn(history,'reader','plan'),lock)
    lead=turn([],'lead','review');team['lead']['history']=lead['messages']
    plan_id=next(iter(state));pending_before=state[plan_id]['status']
    # Only the recipient's boundary commits the plan decision.
    consume_responses(state,team,directory,'reader',lock)
    work=run_teammate(team,'reader',lambda history:turn(history,'reader','work',plan_id),lock)
    close=open_request(state,team,directory,'lead','reader','shutdown','本次工作结束，请在空闲边界关闭。',lock)
    ack=reply_request(state,team,directory,close['request_id'],'reader',True,'本轮已结束，可以关闭。',lock)
    shutdown_before=state[close['request_id']]['status']
    consume_responses(state,team,directory,'lead',lock)
    blocked=run_teammate(team,'reader',lambda _: (_ for _ in ()).throw(AssertionError('closed callback ran')),lock)
    return {'state':state,'team':team,'first':first,'work':work,'ack':ack,'blocked':blocked,'traces':traces,
            'pending_before':pending_before,'shutdown_before':shutdown_before}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision',choices=['allow','deny'],default='deny')
    parser.add_argument('--plan',choices=['approve','reject'],default='approve')
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace');parser.add_argument('--maildir',type=Path)
    args=parser.parse_args()
    def show(folder):
        result=demo(folder,args.workspace.resolve(),args.plan=='approve',args.decision=='allow')
        print('固定模型；真实文件邮箱与获准后的Python进程；无在线模型。')
        print('回复保存后、匹配前：',result['pending_before'],'；退出确认保存后、Lead匹配前：',result['shutdown_before'])
        print('请求终态：',[(key,value['status']) for key,value in result['state'].items()]);print(result['work']['text'])
        print('reader生命周期：',result['team']['reader']['status'],'；再次交付：',result['blocked']['status'])
    if args.maildir:show(args.maildir)
    else:
        with tempfile.TemporaryDirectory(prefix='s16-protocol-') as folder:show(Path(folder))
if __name__=='__main__':main()
