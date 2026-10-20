from figure_fixtures import CASES,fixture_context,FUNCTIONS
import inspect
count=0
for name,cases in CASES.items():
 for case in cases:
  ctx=fixture_context(name,case);env={};exec(ctx['setup'],env);exec(inspect.getsource(next(f for f in FUNCTIONS if f.__name__==name)),env);exec(ctx['entry'],env);out=env['observed']
  if name=='scan_ready':
   if case=='invalid':assert 'error' in out
   else:assert out=={'ready':['expected','source'],'blocked':[],'unlocked':['verify'],'owned':['expected'],'empty':[]}[case]
  if name=='claim_next':
   if case=='save_error':assert 'error' in out
   else:assert out['status']=={'claimed':'claimed','stale':'claimed','busy':'busy','blocked':'idle'}.get(case,'unavailable')
   if case=='stale':assert out['task']['id']=='source' and env['board']['tasks']['expected']['owner'] is None
  if name=='idle_poll':
   if case in ('bad_checks','shutdown_failure'):assert 'error' in out
   else:assert out['status']=={'task':'claimed','shutdown':'shutdown','timeout':'idle_timeout','wakeup':'claimed','busy':'unavailable','interrupted':'interrupted'}[case]
   if case=='shutdown':assert env['team']['reader']['status']=='closed' and env['load_board'](env['directory'])['tasks']['expected']['owner'] is None
  count+=1
print('PASS',count,'same-source teaching inputs')
