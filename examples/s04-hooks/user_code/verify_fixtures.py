import contextlib
import inspect
import io
from figure_fixtures import FUNCTIONS,CASES,fixture_context
for function in FUNCTIONS:
    name=function.__name__
    for scenario in CASES[name]:
        context=fixture_context(name,scenario);ns={}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(context['setup'],ns);exec(inspect.getsource(function),ns);exec(context['entry'],ns)
        if name=='run_hooks':
            assert ns['visited']==(['first'] if scenario in ('block','pre_error') else ['first','second'])
            assert (ns['outcome']['blocked'] is not None)==(scenario in ('block','pre_error'))
            assert len(ns['outcome']['warnings'])==(scenario=='post_error')
        elif name=='execute_hooked':
            denied=scenario in ('block','refused')
            assert ns['_executions']==([] if denied else ['run_main'])
            assert ns['outcome']['result']['tool_use_id']=='run_1'
            assert ns['outcome']['result']['is_error']==denied
            assert len(ns['outcome']['warnings'])==(scenario=='post_error')
        else:
            assert len(ns['entries'])==1 and ns['entries'][0]['id']=='run_1'
            assert ('is_error' in ns['entries'][0])==(scenario!='before')
        print(name,scenario,'PASS')
