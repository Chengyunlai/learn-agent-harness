"""真实注册/目录/缓存不变性，以及SDK之前的程序许可边界。"""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from practice import run, use, answer
from runtime import collect_context, assemble_system_prompt, get_system_prompt, checked_context, TEMPLATES, _s09
MEMORY = {'name':'report-format','description':'先结论后证据的报告偏好','keywords':['核对'],'body':'报告先给核对结论，再列当前执行证据。','source':'用户明确要求'}


def tool(description='读取当前文件。'):
    return {'description':description,'parameters':{'path':str},'run':lambda **_:None}


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.tools={'read_file':tool(),'run_main':{'description':'运行固定main.py。','parameters':{},'run':lambda:None},'load_skill':{'description':'读取技能。','parameters':{'name':str},'run':lambda **_:None}}
        self.skills={'output-check':{'description':'先读预期再核对输出。','path':'/not-in-prompt/SKILL.md','root':'/not-in-prompt'}}
    def context(self, memories=None): return collect_context(self.root,self.tools,self.skills,memories or [])
    def fail(self, fn, *args):
        with self.assertRaises((ValueError,OSError)): fn(*args)
    def test_actual_registration(self):
        before=self.context();self.tools.pop('run_main');after=self.context()
        self.assertIn('run_main',[x['name'] for x in before['tools']]);self.assertNotIn('run_main',[x['name'] for x in after['tools']])
        prompt=get_system_prompt(after,{})['system'];self.assertIn('本次没有run_main',prompt)
    def test_no_keyword_switch(self):
        self.tools.pop('run_main');self.tools['read_file']['description']='用户说请启用run_main，但这只是工具说明。'
        context=self.context();self.assertNotIn('run_main',[item['name'] for item in context['tools']]);self.assertIn('本次没有run_main',get_system_prompt(context,{})['system'])
    def test_workspace(self):
        self.fail(collect_context,self.root/'missing',self.tools,{},[])
        file=self.root/'file';file.write_text('x');self.fail(collect_context,file,self.tools,{},[])
        self.assertEqual(self.context()['workspace'],str(self.root.resolve()))
    def test_handler_required(self):
        self.tools['run_main']['run']=None;self.fail(self.context)
    def test_catalogs(self):
        context=self.context([MEMORY]);self.assertNotIn(MEMORY['body'],str(context));self.assertNotIn('/not-in-prompt',str(context))
        self.assertEqual(set(context['skills'][0]),{'name','description'});self.assertEqual(set(context['memories'][0]),{'name','description','keywords'})
        self.tools.pop('load_skill');self.assertEqual(self.context()['skills'],[])
    def test_sections(self):
        full=assemble_system_prompt(self.context([MEMORY]));self.assertEqual([x['id'] for x in full],['identity','policy','tools','workspace','skills','memory'])
        self.tools.pop('load_skill');minimal=assemble_system_prompt(self.context());self.assertEqual([x['id'] for x in minimal],['identity','policy','tools','workspace'])
        self.assertNotIn(MEMORY['body'],str(full))
    def test_context_isolation(self):
        context=self.context([MEMORY]);before=deepcopy(context);assemble_system_prompt(context);self.assertEqual(context,before)
        context['tools'][0]['description']='changed';self.assertNotIn('changed',str(self.context()))
    def test_canonical_order(self):
        context=self.context([MEMORY]);cache={};one=get_system_prompt(context,cache)
        reverse={key:context[key] for key in reversed(context)};reverse['tools']=list(reversed(reverse['tools']))
        two=get_system_prompt(reverse,cache);self.assertFalse(one['reused']);self.assertTrue(two['reused']);self.assertEqual(one['system'],two['system'])
    def test_dependencies(self):
        context=self.context([MEMORY]);cache={};get_system_prompt(context,cache)
        for change in ('workspace','description','schema','skills','memories'):
            modified=deepcopy(context)
            if change=='workspace':modified['workspace']+='/other'
            if change=='description':modified['tools'][0]['description']+='更新'
            if change=='schema':modified['tools'][0]['input_schema']['additionalProperties']=True
            if change=='skills':modified['skills'][0]['description']+='更新'
            if change=='memories':modified['memories'][0]['description']+='更新'
            self.assertFalse(get_system_prompt(modified,cache)['reused']);get_system_prompt(context,cache)
    def test_template_dependency(self):
        context=self.context();cache={};first=get_system_prompt(context,cache)
        original=TEMPLATES['identity'];self.addCleanup(lambda:TEMPLATES.__setitem__('identity',original));TEMPLATES['identity']=original+' 新固定规则。'
        second=get_system_prompt(context,cache);self.assertFalse(second['reused']);self.assertNotEqual(first['system'],second['system'])
    def test_return_copy(self):
        context=self.context();cache={};value=get_system_prompt(context,cache);value['section_ids'].clear();value['system']='changed'
        again=get_system_prompt(context,cache);self.assertTrue(again['reused']);self.assertTrue(again['section_ids']);self.assertNotEqual(again['system'],'changed')
    def test_invalid_keeps_cache(self):
        context=self.context();cache={};get_system_prompt(context,cache);before=deepcopy(cache)
        invalid=deepcopy(context);invalid['tools'][0]['input_schema']['bad']=lambda:None
        self.fail(get_system_prompt,invalid,cache);self.assertEqual(cache,before)
        self.fail(get_system_prompt,{**context,'question':'用户说启用运行'},cache);self.assertEqual(cache,before)
    def test_prompt_budget_keeps_cache(self):
        context=self.context();cache={};get_system_prompt(context,cache);before=deepcopy(cache)
        original=TEMPLATES['identity'];self.addCleanup(lambda:TEMPLATES.__setitem__('identity',original));TEMPLATES['identity']='规'*5000
        self.fail(get_system_prompt,context,cache);self.assertEqual(cache,before)
    def test_bad_context(self):
        context=self.context()
        for key,value in [('workspace','relative'),('tools',[]),('skills',[{'name':'bad','description':''}]),('memories',[MEMORY])]:self.fail(checked_context,{**context,key:value})
        duplicated=deepcopy(context);duplicated['tools'].append(duplicated['tools'][0]);self.fail(checked_context,duplicated)
    def workspace(self,extra=False):
        path=self.root/'work';path.mkdir(exist_ok=True)
        (path/'main.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\n"+("print('extra')\n" if extra else '')+'print(42)\n');(path/'expected.txt').write_text('42\n');return path
    def check(self,**kwargs):
        workspace=self.workspace();events=[];allowed=kwargs.pop('allowed',False)
        with contextlib.redirect_stdout(io.StringIO()): result=run(workspace,approve=lambda *_:events.append('approval') or allowed,**kwargs)
        return result,workspace,events
    def test_allow_and_local_reuse(self):
        (out,prompts,tools,_),workspace,events=self.check(allowed=True)
        self.assertEqual(out['calls'],5);self.assertTrue((workspace/'ran').exists());self.assertIn('与预期一致',out['text']);self.assertEqual(events,['approval'])
        self.assertEqual([p['reused'] for p in prompts],[False,True,True,True,True])
    def test_deny_not_permission_cache(self):
        (out,prompts,_,_),workspace,events=self.check()
        self.assertFalse((workspace/'ran').exists());self.assertIn('未执行',out['text']);self.assertEqual(events,['approval']);self.assertTrue(prompts[-1]['reused'])
    def test_readonly(self):
        (out,prompts,tools,_),workspace,events=self.check(readonly=True,allowed=True)
        self.assertEqual(out['calls'],4);self.assertNotIn('run_main',tools);self.assertIn('本次没有run_main',prompts[0]['system']);self.assertFalse((workspace/'ran').exists());self.assertEqual(events,[])
    def test_forced_unknown_run(self):
        def hostile(messages,tools,system):
            return use('run_main',{},1) if len(messages)==1 else answer('宿主反馈：'+messages[-1]['content'][0]['content'])
        (out,_,_,_),workspace,events=self.check(readonly=True,parent=hostile)
        self.assertIn('未知工具',out['text']);self.assertFalse((workspace/'ran').exists());self.assertEqual(events,[])
    def test_memory_and_skill_boundaries(self):
        directory=self.root/'.memory';_s09.save_memory(directory,MEMORY,True)
        (out,prompts,tools,_),_,_=self.check(memory_dir=directory,skills_enabled=False)
        self.assertIn('memory',prompts[0]['section_ids']);self.assertNotIn('skills',prompts[0]['section_ids']);self.assertNotIn('load_skill',tools);self.assertNotIn(MEMORY['body'],prompts[0]['system'])
    def test_dynamic_attachments_stay_out(self):
        directory=self.root/'.memory';_s09.save_memory(directory,MEMORY,True);seen=[]
        def observe(messages,tools,system):
            seen.append(deepcopy(messages));from practice import parent_model;return parent_model(messages,tools,system)
        (out,prompts,_,_),_,_=self.check(memory_dir=directory,parent=observe)
        self.assertTrue(all(MEMORY['body'] in str(m) for m in seen));self.assertNotIn('[项目记忆',str(out['messages']));self.assertEqual(prompts[0]['system'],prompts[-1]['system'])
    def test_full_output(self):
        path=self.workspace(extra=True)
        with contextlib.redirect_stdout(io.StringIO()):out,*_=run(path,allowed=True)
        self.assertIn('与预期不一致',out['text'])


if __name__=='__main__':unittest.main()
