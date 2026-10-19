import contextlib
import inspect
import io
from figure_fixtures import FUNCTIONS,CASES,fixture_context
count=0
for fn in FUNCTIONS:
 for case in CASES[fn.__name__]:
  ctx=fixture_context(fn.__name__,case);env={}
  with contextlib.redirect_stdout(io.StringIO()):
   exec(compile(ctx['setup'],'<teaching-fixture>','exec'),env)
   exec(compile(inspect.getsource(fn),'<teaching-code>','exec'),env)
   exec(compile(ctx['entry'],'<teaching-entry>','exec'),env)
  out=env['observed']
  if case in ('new','ready','done'):
   assert 'error' not in out,(fn.__name__,case,out)
   if case=='done':assert out['unlocked']==['report']
  else:assert 'error' in out,(fn.__name__,case,out)
  count+=1
print('PASS',count,'same-source file fixtures; failed operations keep original bytes')
