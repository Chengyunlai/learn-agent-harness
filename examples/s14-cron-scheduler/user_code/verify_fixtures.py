import inspect
from figure_fixtures import CASES, FUNCTIONS, fixture_context
for fn in FUNCTIONS:
    for case in CASES[fn.__name__]:
        ctx=fixture_context(fn.__name__,case); ns={};exec(ctx['setup'],ns);exec(inspect.getsource(fn),ns);exec(ctx['entry'],ns)
        out=ns['observed']
        if fn.__name__=='cron_matches':
            if case in ('invalid','naive'):assert 'error' in out
            else:assert out is (case!='not_due')
        elif fn.__name__=='enqueue_due':
            assert len(out)==int(case in ('due','once'))
            if case=='full':assert ns['state']['jobs']['cron-1']['last_slot'] is None
            if case=='once':assert not ns['state']['jobs'] and len(ns['state']['queue'])==1
        else:
            expected={'ready':'answered','busy':'busy','active':'busy','empty':'idle','failed':'turn_error','model_stop':'call_limit'}[case]
            assert out['status']==expected
            assert len(ns['received'])==int(case in ('ready','failed','model_stop'))
print('PASS 18 original-function teaching contexts')
