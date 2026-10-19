from figure_fixtures import CASES,fixture_context,FUNCTIONS
import inspect
count=0
for name,cases in CASES.items():
    for case in cases:
        ctx=fixture_context(name,case);env={};exec(ctx['setup'],env);exec(inspect.getsource(next(f for f in FUNCTIONS if f.__name__==name)),env);exec(ctx['entry'],env)
        result=env['observed']
        if 'error' in result:assert env['state']==env['before']
        if name=='open_request':assert ('error' in result)==(case not in ('plan','shutdown'))
        if name=='reply_request':
            if case=='busy':assert result['status']=='deferred' and env['state']==env['before'] and env['team']['reader']['active']
            if case in ('approve','reject'):assert env['state'][env['request_id']]['status']=='pending'
        if name=='reply_request' and case=='closed':assert env['team']['reader']['status']=='closed' and env['state'][env['request_id']]['status']=='pending'
        if name=='match_response':assert result['status']=={'approved':'approved','rejected':'rejected','duplicate':'duplicate'}.get(case,'ignored')
        count+=1
print('PASS',count,'same-source teaching inputs')
