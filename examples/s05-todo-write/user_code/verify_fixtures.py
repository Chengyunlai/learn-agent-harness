import contextlib
import inspect
import io
from figure_fixtures import FUNCTIONS,CASES,fixture_context
for function in FUNCTIONS:
 for case in CASES[function.__name__]:
  ns={};ctx=fixture_context(function.__name__,case)
  with contextlib.redirect_stdout(io.StringIO()):
   exec(ctx['setup'],ns);exec(inspect.getsource(function),ns);exec(ctx['entry'],ns)
  if function.__name__=='validate_todos':assert isinstance(ns['outcome'],list)==(case=='valid')
  elif function.__name__=='write_todos':
   assert len(ns['state']['items'])==(0 if case=='clear' else 2)
   assert ns['state']['items'][-1]['status']==('pending' if case=='invalid' else 'completed' if case=='claim' else 'in_progress') if case!='clear' else True
  else:
   assert '宿主提供的当前清单' in ns['outcome'][0]['content']
   assert '宿主提供的当前清单' not in ns['messages'][0]['content']
   assert ns['outcome'][1:]==ns['messages'][1:]
  print(function.__name__,case,'PASS')
