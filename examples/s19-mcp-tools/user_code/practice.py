"""固定模型，官方MCP SDK真实stdio子进程；不访问在线模型或外部业务服务。"""
import argparse
import asyncio
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import *
from runtime import _s07,_s10,_s11

class SessionBridge:
    """同步旧循环在工作线程；官方异步session始终留在创建它的事件循环。"""
    def __init__(self, session, loop):self.session,self.loop=session,loop
    def wait(self, coroutine):
        future=asyncio.run_coroutine_threadsafe(coroutine,self.loop)
        try:return future.result(timeout=6).model_dump(mode='json',by_alias=True,exclude_none=True)
        except BaseException:
            future.cancel();raise
    def list_page(self,cursor):return self.wait(self.session.list_tools(cursor=cursor))
    def call(self,name,args):return self.wait(self.session.call_tool(name,arguments=args))


def fixed_model(messages):
    replies=sum(m['role']=='assistant' for m in messages)
    results=[b for m in messages if isinstance(m['content'],list) for b in m['content'] if b.get('type')=='tool_result']
    if results and results[-1]['is_error']:return _s10.answer('本次未能取得完整证据：'+results[-1]['content'])
    if replies<3:
        name,args=[('load_docs_tools',{}),('mcp__docs__search_docs',{'query':'运行许可'}),('read_file',{'path':'policy.txt'})][replies]
        return _s10.use(name,args,replies+1)
    return _s10.answer('服务规范与本地策略一致：运行需要本次许可；两份工具反馈已保存在历史中。')


def run_example(root,bridge,allowed=False,send_override=None):
    builtins=_s07._s02.build_tools(root);builtins.pop('run_main')
    pool={'current':None};active={'snapshot':None};cache={};requests=[];events=[]
    def load():
        discovered=discover_tools(bridge.list_page)
        candidate=assemble_tool_pool(_s07._s02.tool_definitions(builtins),{'docs':{'tools':discovered,'call':bridge.call}})
        pool['current']=candidate
        return '已接入：'+', '.join(candidate['routes'])
    builtins['load_docs_tools']={'description':'读取宿主已连接的本地docs服务目录，验证后加入本会话工具池。','parameters':{},'run':load}
    pool['current']=assemble_tool_pool(_s07._s02.tool_definitions(builtins),{})
    recovery={'remaining':20,'waited':0.0,'events':[]}
    def ask(messages):
        current=pool['current'];active['snapshot']=current
        # From one pool snapshot derive prompt inputs, SDK definitions and call routing.
        registered=dict(builtins)
        for spec in current['definitions']:
            if spec['name'] in current['routes']:
                registered[spec['name']]={'description':spec['description'],'parameters':{key:str for key in spec['input_schema']['properties']},'run':lambda **_:None}
        context=_s10.collect_context(root,registered,{},[])
        system=_s10.get_system_prompt(context,cache)
        request={'model':'teaching-model','system':system['system'],'tools':deepcopy(current['definitions']),'messages':messages,'max_tokens':1024}
        requests.append(deepcopy(request));events.append({'names':[x['name'] for x in request['tools']],'reused':system['reused']})
        return _s11.request_with_recovery(send_override or (lambda req:fixed_model(req['messages'])),request,recovery,pause=lambda _:None,random_unit=lambda:0)
    def guard(call,tools,ask_user,blocked=()):
        if call['name'] in active['snapshot']['routes']:return call_external(call,active['snapshot'],ask_user)
        if call['name']=='load_docs_tools':return _s07._s02.execute_tool(call,tools)
        return _s07._s04.execute_guarded(call,tools,ask_user,blocked)
    def execute(call):
        tools=dict(builtins)
        for spec in active['snapshot']['definitions']:
            if spec['name'] in active['snapshot']['routes']:
                tools[spec['name']]={'description':spec['description'],'parameters':{k:str for k in spec['input_schema']['properties']},'run':lambda **_:None}
        return _s07._s04.execute_hooked(call,tools,lambda *_:allowed,{},guard=guard)['result']
    outcome=run_loop(ask,execute,max_calls=4,emit=lambda _:None,question='查docs服务的运行许可规则，再读policy.txt，说明两者是否一致。')
    return {'outcome':outcome,'requests':requests,'events':events,'pool_names':[x['name'] for x in pool['current']['definitions']]}


async def demo(root,allowed=False,mode='normal',send_override=None):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise ValueError('需要空实验目录。')
    (root/'policy.txt').write_text('默认拒绝；每次运行main.py都要单独确认。',encoding='utf-8')
    journal=root/'mcp.jsonl'
    params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name('server.py')),mode,str(journal)],cwd=str(root))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=5)) as session:
            initialized=await session.initialize()
            if initialized.capabilities.tools is None:raise ValueError('服务未声明tools能力。')
            bridge=SessionBridge(session,asyncio.get_running_loop())
            result=await asyncio.to_thread(run_example,root,bridge,allowed,send_override)
            result['protocol']=initialized.protocolVersion
    result['mcp_events']=[json.loads(line) for line in journal.read_text().splitlines()]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--decision',choices=['allow','deny'],default='deny');parser.add_argument('--mode',choices=['normal','tool_error','bad_schema'],default='normal');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='s19-mcp-') as d:result=asyncio.run(demo(Path(d),args.decision=='allow',args.mode))
    print('固定模型；官方SDK真实stdio与本地文件；无在线模型或外部业务服务。')
    print(json.dumps({key:value for key,value in result.items() if key!='requests'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
