"""原函数与归档helper真实执行；摘要为固定文本替身，文件仅在临时目录。"""
import inspect
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import checked_exchange,split_history,trim_results,history_bytes,prepare_context,archive_writer
FUNCTIONS=(split_history,trim_results,prepare_context)
CASES={'split_history':['normal','pending','mismatch','multi'],
       'trim_results':['old','recent','error'],
       'prepare_context':['fit','trim','summary','bad_summary','archive_error','recent_large','exhausted']}


def fixture_context(name,scenario):
    if scenario not in CASES[name]:raise ValueError('unknown scenario')
    setup='''from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
import tempfile
scenario=SCENARIO
question="先检查，再获准运行。"
def pair(number,text,error=False):
    return [{"role":"assistant","content":[{"type":"tool_use","id":"call_"+str(number),"name":"read_file","input":{"path":"notes.txt"}}]}, {"role":"user","content":[{"type":"tool_result","tool_use_id":"call_"+str(number),"content":text,"is_error":error}]}]
messages=[{"role":"user","content":question}]+pair(1,"old"*400)+pair(2,"近期证据。")
if scenario=="pending":messages.pop()
if scenario=="mismatch":messages[-1]["content"][0]["tool_use_id"]="wrong"
if scenario=="multi":
    messages[1]["content"].append({"type":"tool_use","id":"second","name":"read_file","input":{"path":"other.txt"}})
    messages[2]["content"].append({"type":"tool_result","tool_use_id":"second","content":"另一条结果","is_error":False})
if scenario=="error":messages[2]["content"][0]["is_error"]=True
if scenario=="recent":messages[-1]["content"][0]["content"]="R"*1600
if scenario=="fit":messages=[{"role":"user","content":question}]+pair(1,"短结果。")
if scenario=="trim":messages=[{"role":"user","content":question}]+pair(1,"A"*1200)+pair(2,"B"*1200)+pair(3,"近期证据。")
if scenario in ("summary","bad_summary","archive_error","exhausted"):
    messages=[{"role":"user","content":question}]
    for i in range(4):messages+=pair(i,"旧"*180)
    messages+=pair(4,"近期证据。")
if scenario=="recent_large":messages=[{"role":"user","content":question}]+pair(1,"R"*2400)
before=deepcopy(messages)
state={"archives":[],"summaries":0,"max_summaries":0 if scenario=="exhausted" else 2}
_temp=tempfile.TemporaryDirectory(prefix="lesson8-")
'''.replace('SCENARIO',repr(scenario))
    for helper in (checked_exchange,split_history,trim_results,history_bytes,archive_writer):
        if helper.__name__!=name:setup+='\n'+inspect.getsource(helper)
    setup+='''
archive=archive_writer(Path(_temp.name))
if scenario=="archive_error":
    def archive(_):raise OSError("教学归档失败")
def summarize(prefix):
    return "" if scenario=="bad_summary" else "旧正文已归档；仍须检查当前文件并取得运行许可。"
'''
    if name=='trim_results':setup+='receipt=archive(messages)\n'
    call={'split_history':'split_history(messages,keep_recent=1)','trim_results':'trim_results(messages,receipt,keep_recent=1)','prepare_context':'prepare_context(messages,question,state,archive,summarize,budget=1600)'}[name]
    entry='try:\n    observed='+call+'\n    print("已生成候选；原历史保持不变。")\nexcept (ValueError,OSError) as error:\n    observed={"error":str(error)}\n    print(str(error))\nassert messages==before\n'
    watch={'split_history':['messages','index','groups','cut','observed'],
           'trim_results':['candidate','parts','index','slot','block','observed'],
           'prepare_context':['messages','state','candidate','parts','summary','observed']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
