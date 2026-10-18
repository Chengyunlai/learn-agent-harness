"""真实标记文件证明是否执行；检查次序、故障时机与消息完整性。"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from runtime import QUESTION, audit_event, build_tools, execute_hooked, run_hooks, run_loop
from practice import build_hooks, scripted_model


class HookChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'main.py').write_text("from pathlib import Path\np=Path('ran')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nprint(42)\n")
        self.tools = build_tools(self.root)
        self.call = {'type': 'tool_use', 'id': 'run_1', 'name': 'run_main', 'input': {}}

    def execute(self, hooks=None, approve=None, blocked=()):
        return execute_hooked(self.call, self.tools, approve or (lambda *_: True), hooks or {}, blocked)

    def test_order_first_block_and_after_feedback(self):
        order=[]; entries=[]
        def one(p): order.append(1)
        def two(p): order.append(2); return '维护暂停'
        def three(p): order.append(3)
        hooks={'before':[one,two,three], 'after':[lambda p:audit_event('after',p,entries)]}
        approval=Mock()
        report=self.execute(hooks, approval)
        self.assertEqual(order,[1,2]); approval.assert_not_called()
        self.assertFalse((self.root/'ran').exists())
        self.assertEqual(report['result']['tool_use_id'],'run_1')
        self.assertIn('未执行',entries[0]['content'])

    def test_pre_errors_and_invalid_returns_block(self):
        def broken(p): raise OSError('unavailable')
        for cb in [broken, lambda p:False, lambda p:True, lambda p:'', lambda p:42]:
            self.assertTrue(self.execute({'before':[cb]})['result']['is_error'])
        self.assertFalse((self.root/'ran').exists())

    def test_after_failure_preserves_result_and_runs_next_observer(self):
        entries=[]
        def broken(p): raise OSError('audit unavailable')
        report=self.execute({'after':[broken, lambda p:audit_event('after',p,entries)]})
        self.assertFalse(report['result']['is_error'])
        self.assertIn('42',report['result']['content'])
        self.assertEqual((self.root/'ran').read_text(),'x')
        self.assertEqual(len(report['warnings']),1); self.assertEqual(len(entries),1)

    def test_copies_protect_call_and_result(self):
        def change(p): p['call'].update(name='unknown',id='changed'); p.get('result',{}).update(content='fake')
        report=self.execute({'before':[change], 'after':[change]})
        self.assertFalse(report['result']['is_error']); self.assertIn('42',report['result']['content'])
        self.assertEqual(report['result']['tool_use_id'],'run_1')
        self.assertEqual(self.call['name'],'run_main')

    def test_none_hook_cannot_override_host_denial(self):
        for blocked,answer in [((),False),(('run_main',),True)]:
            report=self.execute({'before':[lambda p:None]},lambda *_:answer,blocked)
            self.assertTrue(report['result']['is_error'])
        self.assertFalse((self.root/'ran').exists())

    def test_invalid_after_return_warns_and_continues(self):
        report=self.execute({'after':[lambda p:'deny']})
        self.assertEqual(len(report['warnings']),1)
        self.assertFalse(report['result']['is_error'])

    def test_program_failure_is_observed(self):
        (self.root/'main.py').write_text('raise RuntimeError("intentional")\n')
        entries=[]; report=self.execute(build_hooks(entries))
        self.assertTrue(report['result']['is_error'])
        self.assertIn('RuntimeError',entries[-1]['content'])

    def test_unexpected_permission_exception_propagates_without_after(self):
        after=Mock()
        def broken(*a): raise RuntimeError('host unavailable')
        with self.assertRaises(RuntimeError): self.execute({'after':[after]},broken)
        after.assert_not_called(); self.assertFalse((self.root/'ran').exists())

    def test_loop_only_receives_protocol_result(self):
        entries=[]; warnings=[]
        def execute(c):
            report=execute_hooked(c,self.tools,lambda *_:True,build_hooks(entries,audit_failure=True))
            warnings.extend(report['warnings']); return report['result']
        outcome=run_loop(scripted_model,execute,question=QUESTION,emit=lambda _:None)
        self.assertEqual(outcome['status'],'answered')
        results=[m['content'][0] for m in outcome['messages'] if m['role']=='user' and isinstance(m['content'],list)]
        self.assertEqual([r['tool_use_id'] for r in results],['read_1','run_1'])
        self.assertTrue(all('warnings' not in r for r in results)); self.assertEqual(len(warnings),2)
        self.assertEqual((self.root/'ran').read_text(),'x')

    def test_registry_snapshot_and_event_validation(self):
        order=[]; hooks={'before':[]}
        def register(p): hooks['before'].append(lambda p:order.append('late'))
        hooks['before'].append(register)
        run_hooks(hooks,'before',{}); self.assertEqual(order,[])
        run_hooks(hooks,'before',{}); self.assertEqual(order,['late'])
        with self.assertRaises(ValueError):run_hooks({},'typo',{})

    def test_budget_still_stops_repeated_blocks(self):
        ask=lambda m:{'stop_reason':'tool_use','content':[self.call]}
        outcome=run_loop(ask,lambda c:execute_hooked(c,self.tools,lambda *_:True,{'before':[lambda p:'stop']})['result'],max_calls=2,emit=lambda _:None)
        self.assertEqual(outcome['status'],'call_limit'); self.assertFalse((self.root/'ran').exists())


if __name__=='__main__': unittest.main()
