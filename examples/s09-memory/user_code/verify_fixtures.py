import inspect
from figure_fixtures import FUNCTIONS, CASES, fixture_context
count=0
for function in FUNCTIONS:
    for case in CASES[function.__name__]:
        scope={};ctx=fixture_context(function.__name__,case)
        exec(ctx['setup'],scope);exec(inspect.getsource(function),scope);exec(ctx['entry'],scope)
        value=scope['observed']
        if case in ('unapproved','invalid','replace_error','unknown','budget'):assert 'error' in value,(function.__name__,case,value)
        elif function.__name__=='select_memories':assert value==([] if case=='none' else ['report-format'])
        elif function.__name__=='prepare_memory':
            assert value[1:]==scope['before'][1:]
            assert (scope['report']['body'] in value[0]['content'])==(case!='none')
            assert scope['sql']['body'] not in value[0]['content']
        count+=1
print('PASS',count,'same-source function bindings; temporary files and input isolation')
