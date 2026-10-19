import contextlib
import io
import inspect
from figure_fixtures import FUNCTIONS,CASES,fixture_context
count=0
for fn in FUNCTIONS:
 for case in CASES[fn.__name__]:
  ctx=fixture_context(fn.__name__,case);env={}
  with contextlib.redirect_stdout(io.StringIO()):
   exec(compile(ctx['setup'],'<teaching-fixture>','exec'),env)
   exec(compile(inspect.getsource(fn),'<teaching-code>','exec'),env)
   exec(compile(ctx['entry'],'<teaching-entry>','exec'),env)
  result=env['observed']
  if fn.__name__=='request_with_recovery':
   if case in ('twice','fatal','exhausted','long_wait','budget'):assert 'error' in result,(case,result)
   else:assert result['stop_reason']=='end_turn'
   if case=='truncated':assert [r['max_tokens'] for r in env['sent']]==[1024,2048]
  if fn.__name__=='retry_delay' and case=='header':assert result==0.7
  if fn.__name__=='classify_failure' and case=='invalid_request':assert result['action']=='stop'
  count+=1
print('PASS',count,'same-body fixtures; no HTTP, tools or actual sleep')
