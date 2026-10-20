"""固定模型；真实文件/压缩归档/获准进程，可选官方MCP stdio；不调用在线模型。"""
import argparse
import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import *
from runtime import _s19,_s07,_s10,_s11
QUESTION='按项目检查规范读main.py，查docs运行规则，运行前问我；核对输出是否42。'

def module_at(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class FixedModel:
    """预设选工具；最终结论从实际反馈判断，不证明真实模型规划能力。"""
    def __init__(self):self.index=0;self.evidence={}
    def __call__(self,request):
        for message in request['messages']:
            if isinstance(message['content'],list):
                for block in message['content']:
                    if block.get('type')=='tool_result':self.evidence[block['tool_use_id']]=block
        if self.evidence and any(x['is_error'] for x in self.evidence.values()):return _s10.answer('缺少本次证据，停止；没有通过验证。')
        sequence=[('load_skill',{'name':'check'}),('read_file',{'path':'main.py'}),('mcp__docs__search_docs',{'query':'运行许可'}),('run_main',{})]
        if self.index<len(sequence):
            name,args=sequence[self.index];self.index+=1;return _s10.use(name,args,self.index)
        result=self.evidence.get('step_4',{})
        return _s10.answer('验证通过：42。' if result.get('content')=='exit_code=0\n42' and not result.get('is_error') else '输出不符，没有通过验证。')

class LocalDocs:
    """标准库路径的明确替身；真实MCP路径用官方SDK替换这两个接口。"""
    def __init__(self):self.calls=[]
    def list_page(self,cursor):
        return {'tools':[{'name':'search.docs','description':'查询运行许可规则','inputSchema':{'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}}]}
    def call(self,name,args):
        self.calls.append(name);return {'content':[{'type':'text','text':'默认拒绝；每次运行main.py都要单独确认。'}],'isError':False}

def seed(root,mismatch=False):
    root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise ValueError('需要空实验目录。')
    (root/'main.py').write_text('# 教学背景资料 '+('x'*900)+'\nprint('+('43' if mismatch else '42')+')\n',encoding='utf-8')
    directory=root/'.skills'/'check';directory.mkdir(parents=True)
    (directory/'SKILL.md').write_text('---\nname: check\ndescription: 检查程序输出\n---\n读取源码、查询规则，运行前单独确认，逐字核对输出42。',encoding='utf-8')
    memory={'name':'check-style','description':'项目核对习惯','keywords':['检查'],'body':'只按本次完整运行输出核对，不用旧许可。','source':'宿主确认的实验设置'}
    _s10._s09.save_memory(root/'.memory',memory,approved=True)

def run_example(root,bridge,allowed=False,mode='normal',send_override=None,max_calls=5):
    skills=_s07.scan_skills(root/'.skills');records=_s10._s09.load_memory(root/'.memory')
    tools=_s07._s02.build_tools(root)
    tools['load_skill']={'description':'读取项目检查规范','parameters':{'name':str},'run':lambda name:_s07.load_skill(name,skills)}
    pool=_s19.assemble_tool_pool(_s07._s02.tool_definitions(tools),{'docs':{'tools':_s19.discover_tools(bridge.list_page),'call':bridge.call}})
    registered=dict(tools)
    registered['mcp__docs__search_docs']={'description':pool['definitions'][-1]['description'],'parameters':{'query':str},'run':lambda **_:None}
    context=_s10.collect_context(root,registered,skills,records);cache={};requests=[];events=[];closed=[];audit=[]
    compact_state={'archives':[],'summaries':0,'max_summaries':1}
    def compact(history):
        if mode=='context_error':raise ValueError('实验归档故障')
        return _s10._s08.prepare_context(history,QUESTION,compact_state,_s10._s08.archive_writer(root/'archives'),lambda _:'已读检查规范与源码；待查询规则并按本次许可运行。',budget=1700,keep_recent=1)
    selected=_s10._s09.select_memories(_s10._s09.memory_catalog(records),QUESTION)
    def prepare(history):return prepare_turn(history,compact,lambda messages:_s10._s09.prepare_memory(messages,records,selected),lambda:[])
    def capabilities():
        system=_s10.get_system_prompt(context,cache);events.append({'reused':system['reused']})
        return {'builtins':dict(tools),'pool':pool,'system':system['system']}
    model=FixedModel()
    def send(request):
        requests.append(deepcopy(request))
        if mode=='model_error':raise ValueError('实验模型请求故障')
        return send_override(request,model) if send_override else model(request)
    def before(payload):
        _s07._s04.audit_event('before',payload,audit)
        return '实验前置阻止' if mode=='blocked' and payload['call']['name']=='run_main' else None
    def after(payload):
        _s07._s04.audit_event('after',payload,audit)
        if mode=='observer_error':raise ValueError('实验观察故障')
    def close():
        closed.append('host-finish')
        if mode=='close_error':raise OSError('实验收尾故障')
    report=run_session(QUESTION,capabilities,prepare,send,lambda *_:allowed,{'before':[before],'after':[after]},close,max_calls)
    results=[b for m in report['outcome'].get('messages') or [] if isinstance(m['content'],list) for b in m['content'] if b.get('type')=='tool_result']
    run=[x for x in audit if x['event']=='after' and x['tool']=='run_main']
    verified=bool(run and run[-1]['content']=='exit_code=0\n42' and not run[-1]['is_error'])
    return {'report':report,'verified':verified,'requests':requests,'events':events,'audit':audit,'closed':closed,'compact':compact_state,'results':results}

async def real_mcp(root,allowed,mode='normal',send_override=None,max_calls=5):
    from datetime import timedelta
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    previous=module_at('s20_mcp_entry',Path(__file__).resolve().parents[2]/'s19-mcp-tools/user_code/practice.py')
    server=Path(__file__).resolve().parents[2]/'s19-mcp-tools/user_code/server.py';journal=root/'mcp.jsonl'
    params=StdioServerParameters(command=sys.executable,args=[str(server),'normal',str(journal)],cwd=str(root))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=5)) as session:
            initialized=await session.initialize()
            if initialized.capabilities.tools is None:raise ValueError('服务没有tools能力。')
            result=await asyncio.to_thread(run_example,root,previous.SessionBridge(session,asyncio.get_running_loop()),allowed,mode,send_override,max_calls)
            result['protocol']=initialized.protocolVersion
    result['mcp_events']=[json.loads(line) for line in journal.read_text().splitlines()]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--decision',choices=['allow','deny'],default='deny');p.add_argument('--mcp',action='store_true');p.add_argument('--mode',choices=['normal','mismatch','context_error','model_error','blocked','observer_error','close_error'],default='normal');p.add_argument('--max-calls',type=int,default=5);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='s20-integrated-') as d:
        root=Path(d);seed(root,a.mode=='mismatch')
        result=asyncio.run(real_mcp(root,a.decision=='allow',a.mode,max_calls=a.max_calls)) if a.mcp else run_example(root,LocalDocs(),a.decision=='allow',a.mode,max_calls=a.max_calls)
        print('固定模型；真实文件/归档/获准进程；'+('官方MCP真实stdio。' if a.mcp else 'MCP为显式本地替身。'))
        print(json.dumps({k:v for k,v in result.items() if k!='requests'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
