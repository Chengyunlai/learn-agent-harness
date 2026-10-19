"""验证原子提交、请求副本、工具协议和实际执行证据。"""
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import QUESTION, build_tools, execute_with_plan, prepare_messages, run_loop, validate_todos, write_todos
from practice import plan, scripted_model, build_hooks

class TodoChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'main.py').write_text("from pathlib import Path\nPath('ran').touch()\nprint(42)\n")
        (self.root/'expected.txt').write_text('42\n')
        self.state={'items':plan(['in_progress','pending','pending'])}
        self.tools=build_tools(self.root,self.state)
    def test_atomic_failure_on_late_item(self):
        old=deepcopy(self.state)
        for change in ['duplicate','active','unknown','extra','blank','wrong_type']:
            items=plan(['completed','in_progress','pending'])
            if change=='duplicate':items[-1]['id']='1'
            elif change=='active':items[-1]['status']='in_progress'
            elif change=='unknown':items[-1]['status']='done'
            elif change=='extra':items[-1]['approved']=True
            elif change=='blank':items[-1]['content']='  '
            else:items[-1]['content']=42
            with self.assertRaises(ValueError):write_todos(self.state,items)
            self.assertEqual(self.state,old)
    def test_bounds_and_canonical_ids(self):
        for items in [{},[{}]*21,[{'id':'x'*33,'content':'a','status':'pending'}],[{'id':'a','content':'x'*151,'status':'pending'}]]:
            with self.assertRaises(ValueError):validate_todos(items)
        items=[{'id':' 1 ','content':' x ','status':'pending'}]
        self.assertEqual(validate_todos(items),[{'id':'1','content':'x','status':'pending'}])
    def test_commit_copies_and_empty_clears(self):
        items=plan(['completed','pending','pending']);write_todos(self.state,items)
        items[0]['status']='pending';self.assertEqual(self.state['items'][0]['status'],'completed')
        write_todos(self.state,[]);self.assertEqual(self.state['items'],[])
    def test_omission_replaces_not_merges(self):
        write_todos(self.state,[{'id':'3','content':'仅保留这一项','status':'pending'}])
        self.assertEqual([x['id'] for x in self.state['items']],['3'])
    def test_completed_is_not_execution_evidence(self):
        write_todos(self.state,plan(['completed']*3))
        self.assertFalse((self.root/'ran').exists())
    def test_request_has_current_plan_without_mutating_history(self):
        messages=[{'role':'user','content':QUESTION}];old=deepcopy(messages)
        first=prepare_messages(messages,self.state)
        write_todos(self.state,plan(['completed','completed','pending']))
        second=prepare_messages(messages,self.state)
        self.assertNotEqual(first,second);self.assertEqual(messages,old)
        self.assertEqual(second[0]['content'].count('宿主提供的当前清单'),1)
        second[0]['content']='changed';self.assertEqual(messages,old)
    def test_tool_protocol_hooks_and_invalid_plan(self):
        approve=Mock();entries=[]
        for arguments in [{'items':42},{'items':[{'id':'1'}]},{'items':[],'approved':True}]:
            request={'id':'todo_1','name':'todo_write','input':arguments}
            result=execute_with_plan(request,self.tools,approve,build_hooks(entries))['result']
            self.assertEqual(result['tool_use_id'],'todo_1');self.assertTrue(result['is_error'])
        approve.assert_not_called();self.assertFalse((self.root/'ran').exists())
        self.assertEqual(len(entries),6)
    def test_explicit_block_still_blocks_todo_tool(self):
        result=execute_with_plan({'id':'t','name':'todo_write','input':{'items':[]}},self.tools,Mock(),{},('todo_write',))['result']
        self.assertTrue(result['is_error']);self.assertTrue(self.state['items'])
    def test_real_runs_allow_deny_and_maintenance(self):
        for allowed,maintenance in [(False,False),(True,True),(True,False)]:
            marker=self.root/'ran'
            if marker.exists():marker.unlink()
            entries=[];hooks=build_hooks(entries,maintenance)
            outcome=run_loop(lambda m:scripted_model(prepare_messages(m,self.state)),
                lambda c:execute_with_plan(c,self.tools,lambda *_:allowed,hooks)['result'],max_calls=12,emit=lambda _:None,question=QUESTION)
            executed=allowed and not maintenance
            self.assertEqual(marker.exists(),executed)
            self.assertEqual(self.state['items'][-1]['status'],'completed' if executed else 'pending')
            self.assertEqual(outcome['status'],'answered');self.assertEqual(outcome['calls'],8)
    def test_budget_keeps_incomplete_plan(self):
        outcome=run_loop(lambda m:scripted_model(prepare_messages(m,self.state)),lambda c:execute_with_plan(c,self.tools,lambda *_:True,{})['result'],max_calls=4,emit=lambda _:None)
        self.assertEqual(outcome['status'],'call_limit');self.assertFalse((self.root/'ran').exists())
        self.assertIn('pending',[x['status'] for x in self.state['items']])

if __name__=='__main__':unittest.main()
