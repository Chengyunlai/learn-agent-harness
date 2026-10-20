"""官方MCP1.26.0真实stdio初始化/发现/调用/关闭；固定模型，无网络业务服务。"""
import asyncio
import tempfile
from pathlib import Path
from practice import demo

async def main():
    for allowed,mode,expected_calls in [(True,'normal',4),(False,'normal',3),(True,'tool_error',3),(True,'bad_schema',2)]:
        with tempfile.TemporaryDirectory() as d:
            result=await demo(Path(d),allowed,mode)
            assert result['protocol']=='2025-11-25'
            assert result['outcome']['calls']==expected_calls and result['outcome']['status']=='answered'
            calls=[e for e in result['mcp_events'] if e['event']=='tools/call']
            assert len(calls)==(1 if allowed and mode!='bad_schema' else 0)
            if mode=='bad_schema':assert 'mcp__docs__search_docs' not in result['pool_names']
            else:
                assert 'mcp__docs__search_docs' not in result['events'][0]['names']
                assert 'mcp__docs__search_docs' in result['events'][1]['names']
                assert not result['events'][1]['reused']
            if allowed and mode=='normal':assert result['events'][-1]['reused'] and '本地策略一致' in result['outcome']['text']
            print('PASS real MCP stdio',allowed,mode,'logical calls',expected_calls)
    # A real server accepts the request, then exceeds this one call's deadline.
    from datetime import timedelta
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    import sys,json
    from practice import SessionBridge
    import runtime as core
    with tempfile.TemporaryDirectory() as d:
        journal=Path(d)/'calls.jsonl'
        params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name('server.py')),'normal',str(journal)])
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=5)) as session:
                await session.initialize();bridge=SessionBridge(session,asyncio.get_running_loop())
                tools=await asyncio.to_thread(core.discover_tools,bridge.list_page)
                def deadline(name,args):return bridge.wait(session.call_tool(name,args,read_timeout_seconds=timedelta(seconds=.1)))
                pool=core.assemble_tool_pool([],{'docs':{'tools':tools,'call':deadline}})
                out=await asyncio.to_thread(core.call_external,{'id':'slow-1','name':'mcp__docs__search_docs','input':{'query':'slow'}},pool,lambda *_:True)
                assert out['is_error'] and out['tool_use_id']=='slow-1'
                # Timeout does not prove the server stopped: keep its transport alive,
                # observe this fixture's eventual completion, then verify a live ping.
                for _ in range(200):
                    if 'tools/done' in journal.read_text():break
                    await asyncio.sleep(.01)
                else:raise AssertionError('owned slow fixture did not finish')
                await session.send_ping()
        events=[json.loads(line) for line in journal.read_text().splitlines()]
        assert len([e for e in events if e['event']=='tools/call'])==1
        print('PASS real MCP deadline; one accepted call, error receipt, no retry')
if __name__=='__main__':asyncio.run(main())
