"""组合边界的真实文件、归档与进程回归；不用在线模型。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from practice import seed,run_example,LocalDocs
from runtime import prepare_turn,run_session,dispatch_call,freeze_capabilities,_s19,_s07
class Integration(unittest.TestCase):
    def run_case(self,allowed=True,mode='normal',max_calls=5,send=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);seed(root,mode=='mismatch');bridge=LocalDocs();out=run_example(root,bridge,allowed,mode,send,max_calls)
            out['remote_count']=len(bridge.calls);out['archives_actual']=len(list((root/'archives').glob('*.jsonl')))
            return out
    def test_allowed(self):
        out=self.run_case();self.assertTrue(out['verified']);self.assertEqual(out['report']['outcome']['calls'],5);self.assertEqual(out['remote_count'],1);self.assertGreater(out['archives_actual'],0)
        self.assertEqual(out['closed'],['host-finish']);self.assertEqual(len([x for x in out['audit'] if x['event']=='after' and x['tool']=='run_main']),1)
    def test_denied(self):
        out=self.run_case(False);self.assertFalse(out['verified']);self.assertEqual(out['report']['outcome']['status'],'answered');self.assertTrue(all(x['is_error'] for x in out['results'][-1:]));self.assertEqual(out['remote_count'],0)
    def test_wrong_output(self):self.assertFalse(self.run_case(mode='mismatch')['verified'])
    def test_context_error(self):
        out=self.run_case(mode='context_error');self.assertEqual(out['requests'],[]);self.assertEqual(out['report']['outcome']['status'],'context_error');self.assertEqual(out['closed'],['host-finish'])
    def test_model_error(self):
        out=self.run_case(mode='model_error');self.assertEqual(out['report']['outcome']['status'],'model_error');self.assertEqual(out['closed'],['host-finish'])
    def test_blocked(self):
        out=self.run_case(mode='blocked');self.assertFalse(out['verified']);self.assertIn('前置阻止',out['audit'][-1]['content'])
    def test_after_warning(self):
        out=self.run_case(mode='observer_error');self.assertTrue(out['verified']);self.assertEqual(len(out['report']['warnings']),4)
    def test_close_warning(self):
        out=self.run_case(mode='close_error');self.assertTrue(out['verified']);self.assertEqual(out['report']['outcome']['status'],'answered');self.assertIn('收尾失败',out['report']['warnings'][0])
    def test_limit(self):
        out=self.run_case(max_calls=4);self.assertEqual(out['report']['outcome']['status'],'call_limit');self.assertTrue(out['verified']);self.assertEqual(len(out['requests']),4)
    def test_attachment_not_persistent(self):
        out=self.run_case();canonical=out['report']['outcome']['messages'][0]['content'];self.assertNotIn('[项目记忆',canonical)
        for req in out['requests']:self.assertEqual(req['messages'][0]['content'].count('[项目记忆'),1)
    def test_retry_only_request(self):
        failed=[False];requests=[]
        def send(req,model):
            requests.append(deepcopy(req))
            if model.index==4 and not failed[0]:failed[0]=True;return {'failure':{'status':529,'retry_after':'0'}}
            return model(req)
        out=self.run_case(send=send);self.assertTrue(out['verified']);self.assertEqual(len(requests),6);self.assertEqual(requests[-1],requests[-2]);self.assertEqual(out['remote_count'],1)
    def test_candidate_failure(self):
        history=[{'role':'user','content':'检查'}];before=deepcopy(history)
        def attach(candidate):candidate[0]['content']+='记忆';return candidate
        with self.assertRaises(ValueError):prepare_turn(history,lambda x:x,attach,lambda:['x'*241])
        self.assertEqual(history,before)
    def test_snapshot_and_hooks(self):
        source={'builtins':{'read_file':{'description':'read','parameters':{'path':str},'run':lambda path:path}},'pool':{'definitions':[],'routes':{}},'system':'policy'}
        frozen=freeze_capabilities(source);source['builtins']['read_file']['parameters'].clear();self.assertIn('path',frozen['builtins']['read_file']['parameters'])
        calls=[];out=dispatch_call({'id':'x','name':'missing','input':{}},frozen,lambda *_:calls.append('confirm'),{})
        self.assertTrue(out['result']['is_error']);self.assertEqual(calls,[])
    def test_unexpected_tool_failure_cleanup(self):
        closed=[]
        with patch('runtime.dispatch_call',side_effect=RuntimeError('host dispatch failed')):
            result=run_session('检查',lambda:{'builtins':{},'pool':{'definitions':[],'routes':{}},'system':'fixed'},lambda h:{'history':h,'messages':h},lambda _:{'stop_reason':'tool_use','content':[{'type':'tool_use','id':'x','name':'missing','input':{}}]},lambda *_:False,{},lambda:closed.append(1),max_calls=1)
        self.assertEqual(closed,[1]);self.assertEqual(result['outcome']['status'],'host_error');self.assertIsNone(result['outcome']['messages'])
if __name__=='__main__':unittest.main()
