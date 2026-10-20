"""标准库桥接测试；真实MCP进程验证单独在verify_mcp.py。"""
from copy import deepcopy
import unittest
from figure_fixtures import fixture_context,CASES
import runtime as core

def env(name,case):
    ctx=fixture_context(name,case);result={};exec(ctx['setup'],result);return result
class BridgeTests(unittest.TestCase):
    def test_pages_and_no_partial_publish(self):
        state=env('discover_tools','pages');self.assertEqual([t['name'] for t in core.discover_tools(state['list_page'])],['search.docs','read.policy'])
        state=env('discover_tools','bad_schema');old=[{'name':'old'}]
        with self.assertRaises(ValueError):old[:]=core.discover_tools(state['list_page'])
        self.assertEqual(old,[{'name':'old'}]);self.assertEqual(len(state['page_calls']),2)
    def test_pagination_and_limits(self):
        for case in ('duplicate','repeat','limit','many'):
            state=env('discover_tools',case)
            with self.assertRaises(ValueError):core.discover_tools(state['list_page'])
            self.assertLessEqual(len(state['page_calls']),4)
    def test_schema_rejects_unsupported(self):
        state=env('discover_tools','pages')
        for bad in [None,1,[],{'name':2}, {'name':'x','inputSchema':{}}]:
            with self.assertRaises(ValueError):core.checked_tool(bad)
        for modify in [lambda x:x.update(required=[[]]), lambda x:x.update(additionalProperties=True),lambda x:x.update(properties={'query':{'type':'integer'}})]:
            raw=deepcopy(state['a']);modify(raw['inputSchema'])
            with self.assertRaises(ValueError):core.checked_tool(raw)
    def test_same_names_on_two_servers_route_correctly(self):
        state=env('assemble_tool_pool','two');calls=[]
        for server in state['servers']:
            state['servers'][server]['call']=lambda remote,args,s=server:calls.append((s,remote)) or {'content':[{'type':'text','text':s}]}
        pool=core.assemble_tool_pool(state['builtins'],state['servers'])
        for server in ('docs','other'):
            result=core.call_external({'id':server,'name':f'mcp__{server}__search_docs','input':{'query':'q'}},pool,lambda *_:True)
            self.assertEqual(result['content'],server)
        self.assertEqual(calls,[('docs','search.docs'),('other','search.docs')])
    def test_alias_collision_preserves_old_pool(self):
        state=env('assemble_tool_pool','one');old=core.assemble_tool_pool(state['builtins'],state['servers']);before=deepcopy(old['definitions'])
        state['servers']['docs']['tools'].append(state['tool']('search_docs'))
        with self.assertRaises(ValueError):old=core.assemble_tool_pool(state['builtins'],state['servers'])
        self.assertEqual(old['definitions'],before)
    def test_schema_is_a_snapshot(self):
        state=env('assemble_tool_pool','one');pool=core.assemble_tool_pool(state['builtins'],state['servers']);state['servers']['docs']['tools'][0]['inputSchema']['properties'].clear()
        self.assertIn('query',pool['routes']['mcp__docs__search_docs']['schema']['properties'])
    def test_permission_is_not_readonly_hint(self):
        state=env('call_external','deny');out=core.call_external(state['call'],state['pool'],state['ask_user'])
        self.assertTrue(out['is_error']);self.assertEqual(state['remote_calls'],[])
    def test_arguments_and_id_not_changed_by_approval(self):
        state=env('call_external','success');before=deepcopy(state['call']);out=core.call_external(state['call'],state['pool'],state['ask_user'])
        self.assertEqual(state['call'],before);self.assertEqual(out['tool_use_id'],'call_2');self.assertEqual(state['remote_calls'][0]['arguments'],before['input'])
    def test_invalid_arguments_no_call(self):
        state=env('call_external','success')
        for args in ({'query':True},{'query':'x'*121},{'query':'q','other':'x'},[]):
            call={**state['call'],'input':args};self.assertTrue(core.call_external(call,state['pool'],lambda *_:True)['is_error'])
        self.assertEqual(state['remote_calls'],[])
    def test_errors_never_retry_remote_call(self):
        for case in ('tool_error','transport','mixed','oversize'):
            state=env('call_external',case);out=core.call_external(state['call'],state['pool'],state['ask_user']);self.assertTrue(out['is_error']);self.assertEqual(len(state['remote_calls']),1)
    def test_new_tool_waits_for_next_model_request(self):
        import tempfile
        from pathlib import Path
        from practice import run_example
        state=env('call_external','success')
        class Bridge:
            list_page=staticmethod(lambda cursor:{'tools':[state['a']]})
            call=staticmethod(state['invoke'])
        requests=[]
        def send(req):
            requests.append(req)
            if len(requests)==1:
                return {'stop_reason':'tool_use','content':[{'type':'tool_use','id':'load-1','name':'load_docs_tools','input':{}},{'type':'tool_use','id':'premature-2','name':'mcp__docs__search_docs','input':{'query':'q'}}]}
            return {'stop_reason':'end_turn','content':[{'type':'text','text':'已收到未开放工具的拒绝。'}]}
        with tempfile.TemporaryDirectory() as d:result=run_example(Path(d),Bridge(),True,send)
        self.assertEqual(state['remote_calls'],[])
        self.assertNotIn('mcp__docs__search_docs',[t['name'] for t in requests[0]['tools']])
        self.assertIn('mcp__docs__search_docs',[t['name'] for t in requests[1]['tools']])
        self.assertTrue(result['outcome']['messages'][2]['content'][1]['is_error'])
    def test_result_subset_and_error_flag(self):
        for reply in ({'content':[]},{'content':[{'type':'text','text':''}]},{'content':[{'type':'text','text':'x'}],'isError':'false'},{'content':[{'type':'text','text':'x'}],'structuredContent':{'x':1}}):
            with self.assertRaises(ValueError):core.result_text(reply)
if __name__=='__main__':unittest.main()
