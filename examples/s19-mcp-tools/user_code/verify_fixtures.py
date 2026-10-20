from figure_fixtures import CASES,FUNCTIONS,fixture_context
import inspect

def check(name,case,env):
    out=env['observed']
    if name=='discover_tools':
        if case in ('pages','empty'):assert len(out)==(2 if case=='pages' else 0)
        else:assert 'error' in out
        assert len(env['page_calls'])<=4
    elif name=='assemble_tool_pool':
        if case in ('one','two'):assert len(out['routes'])==(1 if case=='one' else 2)
        else:assert 'error' in out
        assert env['builtins']==env['before']
    else:
        assert out['tool_use_id']=='call_2' and out['is_error']==(case!='success')
        assert len(env['remote_calls'])==(0 if case in ('deny','bad_args','unknown') else 1)
        if case=='success':assert env['call']['input']=={'query':'运行许可'}
if __name__=='__main__':
    count=0
    for name,cases in CASES.items():
        for case in cases:
            ctx=fixture_context(name,case);env={};exec(ctx['setup'],env);exec(inspect.getsource(next(f for f in FUNCTIONS if f.__name__==name)),env);exec(ctx['entry'],env);check(name,case,env);count+=1
    print('PASS',count,'same-source fixture inputs; explicit page/call substitutes')
