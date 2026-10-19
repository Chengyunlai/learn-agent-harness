from figure_fixtures import CASES, FUNCTIONS, fixture_context
import inspect
for fn in FUNCTIONS:
    for case in CASES[fn.__name__]:
        ctx = fixture_context(fn.__name__, case); ns = {}
        exec(ctx['setup'], ns); exec(inspect.getsource(fn), ns); exec(ctx['entry'], ns)
        out = ns['observed']
        if fn.__name__ == 'start_background':
            assert out['is_error'] == (case in ('denied', 'invalid', 'full', 'launch_error'))
            assert len(ns['launched']) == (0 if case in ('denied', 'invalid', 'launch_error') else 4 if case == 'full' else 1)
        elif fn.__name__ == 'collect_background':
            assert len(out) == (0 if case == 'running' else 1)
            if case == 'cached':assert ns['jobs']['call_1']['handle'].checks == 1
        else:
            assert len(out) - len(ns['history']) == (0 if case in ('already', 'pending') else 1)
print('PASS 15 original-function teaching contexts')
