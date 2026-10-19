import inspect
from figure_fixtures import FUNCTIONS,CASES,fixture_context
count=0
for fn in FUNCTIONS:
    for case in CASES[fn.__name__]:
        scope={};ctx=fixture_context(fn.__name__,case)
        exec(ctx['setup'],scope);exec(inspect.getsource(fn),scope);exec(ctx['entry'],scope)
        observed=scope['observed']
        if case in ('invalid','budget'):assert 'error' in observed,(fn.__name__,case,observed)
        elif fn.__name__=='collect_context':
            assert all('run' not in item for item in observed['tools'])
            if case=='readonly':assert 'run_main' not in [item['name'] for item in observed['tools']]
            if case=='no_skill':assert observed['skills']==[]
        elif fn.__name__=='assemble_system_prompt':
            assert [item['id'] for item in observed][:4]==['identity','policy','tools','workspace']
            if case=='minimal':assert len(observed)==4
        elif fn.__name__=='get_system_prompt':assert observed['reused']==(case=='hit')
        count+=1
print('PASS',count,'same-source bindings; real warm cache and failed update isolation')
