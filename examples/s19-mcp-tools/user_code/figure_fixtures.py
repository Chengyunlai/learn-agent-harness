"""原样桥接函数；分页与调用接口为可展开的内存替身，不启动MCP子进程。"""
import inspect
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import runtime as core
FUNCTIONS=(core.discover_tools,core.assemble_tool_pool,core.call_external)
CASES={'discover_tools':['pages','empty','duplicate','bad_schema','repeat','limit','many'],
       'assemble_tool_pool':['one','two','collision','builtin_collision','bad_server','unsupported'],
       'call_external':['success','deny','bad_args','unknown','tool_error','transport','mixed','oversize']}

def fixture_context(name,case):
    if case not in CASES[name]:raise ValueError('unknown input')
    setup='from copy import deepcopy\nimport json\nimport re\n'
    for fn in (core.checked_tool,core.result_text,*FUNCTIONS):setup+=inspect.getsource(fn)+'\n'
    setup+='''
scenario=SCENARIO
schema={'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}
def tool(name):return {'name':name,'description':'本地固定文档查询','inputSchema':deepcopy(schema),'annotations':{'readOnlyHint':True}}
a,b=tool('search.docs'),tool('read.policy')
pages=[{'tools':[a],'nextCursor':'p2'},{'tools':[b]}];page_calls=[];remote_calls=[];approvals=[]
def list_page(cursor):
    page_calls.append(cursor)
    if scenario in ('repeat','limit'):return {'tools':[],'nextCursor':'again' if scenario=='repeat' else str(len(page_calls))}
    return deepcopy(pages[0 if cursor is None else 1])
def invoke(remote,arguments):
    remote_calls.append({'name':remote,'arguments':deepcopy(arguments)})
    if scenario=='transport':raise TimeoutError('教学超时；不重发调用')
    if scenario=='mixed':return {'content':[{'type':'image','data':'omitted'}]}
    return {'content':[{'type':'text','text':'x'*2001 if scenario=='oversize' else '运行需要本次许可。'}],'isError':scenario=='tool_error'}
def ask_user(snapshot,server):
    approvals.append(server);snapshot['input'].clear()
    return scenario!='deny'
builtins=[{'name':'read_file','description':'读取本地短文件','input_schema':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}]
servers={'docs':{'tools':[a],'call':invoke}}
if FUNCTION=='discover_tools':
    if scenario=='empty':pages=[{'tools':[]}]
    if scenario=='duplicate':pages[1]={'tools':[a]}
    if scenario=='bad_schema':pages[1]={'tools':[{'name':'later','inputSchema':{'type':'array'}}]}
    if scenario=='many':pages=[{'tools':[tool('t'+str(i)) for i in range(9)]}]
if FUNCTION=='assemble_tool_pool':
    if scenario=='two':servers['other']={'tools':[a],'call':invoke}
    if scenario=='collision':servers['docs']['tools'].append(tool('search_docs'))
    if scenario=='builtin_collision':builtins[0]['name']='mcp__docs__search_docs'
    if scenario=='bad_server':servers={'../docs':servers['docs']}
    if scenario=='unsupported':servers['docs']['tools'][0]['inputSchema']={'type':'array'}
before=deepcopy(builtins)
pool=assemble_tool_pool(builtins,{'docs':{'tools':[a],'call':invoke}}) if FUNCTION=='call_external' else None
call={'id':'call_2','name':'mcp__docs__search_docs','input':{'query':'运行许可'}}
if scenario=='bad_args':call['input']={'path':'main.py'}
if scenario=='unknown':call['name']='mcp__missing__search_docs'
'''.replace('SCENARIO',repr(case)).replace('FUNCTION',repr(name))
    call={'discover_tools':'discover_tools(list_page)','assemble_tool_pool':'assemble_tool_pool(builtins,servers)','call_external':'call_external(call,pool,ask_user)'}[name]
    entry='try:\n    observed='+call+'\n'
    if name=='assemble_tool_pool':entry+="    observed={'names':[x['name'] for x in observed['definitions']], 'routes':{key:{'server':value['server'],'remote':value['remote']} for key,value in observed['routes'].items()}}\n"
    entry+='except (ValueError,TypeError) as error:\n    observed={"error":str(error)}\nprint(observed)\n'
    watch={'discover_tools':['cursor','page','tool','tools','seen','observed'],
           'assemble_tool_pool':['server','tool','alias','definitions','routes','observed'],
           'call_external':['snapshot','route','arguments','reply','failed','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
