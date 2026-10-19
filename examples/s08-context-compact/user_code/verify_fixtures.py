import inspect
from figure_fixtures import FUNCTIONS,CASES,fixture_context
count=0
for function in FUNCTIONS:
    for case in CASES[function.__name__]:
        ctx=fixture_context(function.__name__,case);scope={}
        exec(ctx['setup'],scope);exec(inspect.getsource(function),scope);exec(ctx['entry'],scope)
        value=scope['observed']
        if case in ('pending','mismatch','bad_summary','archive_error','recent_large','exhausted'):assert 'error' in value
        elif function.__name__=='prepare_context':assert type(value) is list
        if function.__name__=='trim_results':
            assert value[2]['content'][0]['tool_use_id']=='call_1'
            assert value[2]['content'][0]['is_error']==(case=='error')
            assert value[-2:]==scope['before'][-2:]
        if case=='summary':assert scope['state']['summaries']==1 and len(value)==3
        count+=1
print('PASS',count,'original-function bindings; input history unchanged')
