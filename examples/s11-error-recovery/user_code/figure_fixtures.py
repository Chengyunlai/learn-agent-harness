"""原样函数、固定响应、可查看的等待记录器；不发请求、不运行工具、不真实睡眠。"""
import inspect
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import classify_failure,retry_delay,request_with_recovery,checked_state,RecoveryStopped
FUNCTIONS=(classify_failure,retry_delay,request_with_recovery)
CASES={'classify_failure':['ready','transient','truncated','invalid_request','denied','unknown'],
       'retry_delay':['backoff','header','invalid','long','bad_jitter'],
       'request_with_recovery':['transient','truncated','twice','fatal','exhausted','long_wait','budget','mutation']}

def fixture_context(name,case):
 if case not in CASES[name]:raise ValueError('unknown case')
 setup='''from copy import deepcopy
import math
import random
import time
scenario=SCENARIO
'''.replace('SCENARIO',repr(case))
 for item in (RecoveryStopped,checked_state,classify_failure,retry_delay):setup+='\n'+inspect.getsource(item)
 setup+='''
ready={'stop_reason':'end_turn','content':[{'type':'text','text':'已有本次执行证据，输出为42。'}]}
partial={'stop_reason':'max_tokens','content':[{'type':'tool_use','id':'partial','name':'run_main','input':{}}]}
request={'messages':[{'role':'user','content':'检查main.py与expected.txt。'}],'max_tokens':1024}
state={'remaining':20,'waited':0.0,'events':[]}
sent=[]
waits=[]
outcome={'ready':ready,'transient':{'failure':{'status':529}},'truncated':partial,'invalid_request':{'failure':{'status':400}},'denied':{'failure':{'status':403}},'unknown':{'stop_reason':'new_reason','content':[]}}.get(scenario,ready)
attempt=1
retry_after={'header':'0.7','invalid':'not-a-number','long':'9'}.get(scenario)
jitter=2 if scenario=='bad_jitter' else 0.5
queue=[{'failure':{'status':529}},ready]
if scenario=='truncated':queue=[partial,ready]
if scenario=='twice':queue=[partial,partial]
if scenario=='fatal':queue=[{'failure':{'status':401}}]
if scenario=='exhausted':queue=[{'failure':{'status':529}}]*4
if scenario=='long_wait':queue=[{'failure':{'status':429,'retry_after':'9'}}]
if scenario=='budget':state['remaining']=0
if scenario=='mutation':queue=[{'failure':{'status':529}},ready]
def send(payload):
    sent.append(deepcopy(payload))
    if scenario=='mutation':payload['messages'].clear()
    return deepcopy(queue.pop(0))
before=deepcopy(request)
'''
 calls={'classify_failure':'classify_failure(outcome)','retry_delay':'retry_delay(attempt,retry_after,jitter)','request_with_recovery':'request_with_recovery(send,request,state,pause=waits.append,random_unit=lambda:0)'}
 entry='try:\n    observed='+calls[name]+'\n    print(observed)\nexcept (ValueError,RecoveryStopped) as error:\n    observed={"error":str(error)}\n    print(str(error))\n'
 if name=='request_with_recovery':entry+='assert request==before\nassert all(not x.get("content") for x in request["messages"] if x["role"]=="assistant")\n'
 watch={'classify_failure':['outcome','status','reason','observed'], 'retry_delay':['attempt','retry_after','jitter','seconds','base','observed'], 'request_with_recovery':['attempt','decision','pending','delay','state','observed']}[name]
 return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
