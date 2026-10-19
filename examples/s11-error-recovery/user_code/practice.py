"""固定故障注入/可选真实API；文件进程与权限仍走前课入口。"""
import argparse
from copy import deepcopy
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
from runtime import _s10, request_with_recovery, sdk_send


def run(workspace, scenario='transient', allowed=False, send_override=None, pause=lambda _: None, request_limit=20, **kwargs):
    recovery = {'remaining': request_limit, 'waited': 0.0, 'events': []}
    sent = []; waits = []; injected = False
    def parent(history, tools, system):
        nonlocal injected
        def send(request):
            nonlocal injected
            sent.append(deepcopy(request))
            if send_override is not None:
                return send_override(request)
            # 默认在run_main已有结果、准备报告的请求上失败，证明不会重跑工具。
            after_run = any(m['role']=='user' and isinstance(m['content'],list) and any(b.get('type')=='tool_result' and str(b.get('content','')).startswith('exit_code=') for b in m['content']) for m in history)
            if scenario == 'exhausted': return {'failure': {'status': 529}}
            if after_run and (not injected or scenario in ('truncated_twice', 'fatal', 'long_wait')):
                injected = True
                if scenario in ('truncated','truncated_twice'):
                    return {'stop_reason':'max_tokens','content':[{'type':'tool_use','id':'partial','name':'run_main','input':{}}]}
                if scenario == 'fatal': return {'failure': {'status': 401}}
                return {'failure': {'status': 429, 'retry_after': '9' if scenario=='long_wait' else '0.25'}}
            return _s10.parent_model(request['messages'],tools,system)
        def wait(seconds):
            waits.append(seconds); pause(seconds)
        request = {'model': 'teaching-model', 'system': system, 'tools': _s10._s07._s05.tool_definitions(tools), 'messages': history, 'max_tokens': 1024}
        return request_with_recovery(send, request, recovery, pause=wait, random_unit=lambda: 0)
    out, prompts, tools, compact = _s10.run(workspace, allowed=allowed, parent=parent, **kwargs)
    return out, recovery, sent, waits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',choices=['transient','truncated','truncated_twice','fatal','long_wait','exhausted'],default='transient')
    parser.add_argument('--decision',choices=['allow','deny'],default='deny')
    parser.add_argument('--workspace',type=Path,default=Path(__file__).parent/'workspace')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args(); send=None; client=None
    if args.live:
        if not os.environ.get('ANTHROPIC_API_KEY') or not os.environ.get('ANTHROPIC_MODEL'):parser.error('--live需要API_KEY与MODEL')
        from anthropic import Anthropic
        import time
        client=Anthropic(timeout=20,max_retries=0)
        def send(request):
            request['model']=os.environ['ANTHROPIC_MODEL'];return sdk_send(client,request)
        pause=time.sleep
    else:pause=lambda _:None
    print('真实API父请求；子模型/摘要仍为固定替身。' if args.live else '固定模型与故障注入；真实文件/获准进程，等待只记录不睡眠。')
    try:
        out,state,sent,waits=run(args.workspace.resolve(),args.scenario,args.decision=='allow',send,pause)
    finally:
        if client is not None:client.close()
    print('父逻辑调用：',out['calls'],'；父请求尝试：',20-state['remaining'])
    print('计划等待秒数：',state['waited']);print('恢复动作：',state['events'])
    print('停止状态：',out['status']);print(out['text'])
    return 0 if out['status']=='answered' else 1

if __name__=='__main__':raise SystemExit(main())
