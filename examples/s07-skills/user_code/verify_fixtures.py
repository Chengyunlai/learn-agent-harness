import inspect
from figure_fixtures import FUNCTIONS,CASES,fixture_context
count=0
for function in FUNCTIONS:
    for case in CASES[function.__name__]:
        c=fixture_context(function.__name__,case);scope={}
        exec(c['setup'],scope);exec(inspect.getsource(function),scope);exec(c['entry'],scope)
        observed=scope['observed']
        if case in ('mismatch','header','unknown','oversize','encoding') or (function.__name__=='load_skill' and case=='empty'):assert 'error' in observed
        elif function.__name__=='scan_skills':assert set(observed)=={'output-check','sql-style'}
        elif function.__name__=='build_system':assert '先读预期，再获准运行' not in observed
        elif case=='found':assert '先读预期，再获准运行' in observed
        count+=1
print('PASS',count,'original-function virtual-file bindings')
