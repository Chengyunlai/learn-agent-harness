from figure_fixtures import CASES,FUNCTIONS,fixture_context
import inspect
for name,cases in CASES.items():
    for case in cases:
        ctx=fixture_context(name,case);env={};exec(ctx['setup'],env);exec(inspect.getsource(next(f for f in FUNCTIONS if f.__name__==name)),env);exec(ctx['entry'],env)
        out=env['observed'];assert env['history']==env['original']
        if name=='prepare_turn':
            if case in ('attached','empty'):assert '[项目记忆]' not in out['history'][0]['content']
            else:assert 'error' in out
        elif name=='dispatch_call':
            assert out['result']['is_error']==(case in ('denied','blocked','unknown'))
            assert len(env['invoked'])==(0 if case in ('denied','blocked','unknown') else 1)
        else:
            assert env['closed']==['closed'];assert len(env['invoked'])<=1
            assert out['outcome']['status']==('call_limit' if case=='limit' else 'context_error' if case=='context_error' else 'model_error' if case=='model_error' else 'host_error' if case=='host_error' else 'answered')
print('PASS',sum(map(len,CASES.values())),'same-source teaching inputs')
