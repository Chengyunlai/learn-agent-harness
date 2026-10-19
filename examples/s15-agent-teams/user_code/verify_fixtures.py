from figure_fixtures import CASES, FUNCTIONS, fixture_context
import inspect
for fn in FUNCTIONS:
    for case in CASES[fn.__name__]:
        ctx=fixture_context(fn.__name__,case);ns={};exec(ctx['setup'],ns);exec(inspect.getsource(fn),ns);exec(ctx['entry'],ns)
        out=ns['observed']
        if fn.__name__=='send_message':assert ('error' in out)==(case!='queued')
        elif fn.__name__=='prepare_inbox':
            if case in ('corrupt','limit'):assert 'error' in out
            else:assert len(out)==(1 if case=='empty' else 2)
        else:
            assert out['status']=={'first':'answered','continued':'answered','busy':'unavailable','exhausted':'unavailable','failed':'failed','stopped':'call_limit'}[case]
            assert len(ns['received'])==int(case not in ('busy','exhausted'))
print('PASS 18 original-function contexts')
