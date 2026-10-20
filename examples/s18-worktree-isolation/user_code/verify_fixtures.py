from figure_fixtures import CASES, fixture_context, FUNCTIONS
import inspect

def check(name, case, env):
    out=env['observed']; bindings=env['bindings']; commands=env['commands']
    errors={'duplicate','claimed','invalid','git_error','limit','wrong_owner','pending','branch_changed','removed','remove_error'}
    if case in errors: assert 'error' in out, (name,case,out)
    elif name=='create_workspace':assert out['status']=='ready' and env['board']['tasks']['alpha']['status']=='pending'
    elif name=='workspace_for_task':
        if case=='busy':assert 'error' in out
        else:assert out.endswith('/alpha') and bindings['alpha']['active']
    else:
        assert out['status']=={'keep':'kept','clean':'removed','dirty':'needs_review','committed':'needs_review','ignored':'needs_review','busy':'busy'}[case]
        assert env['board']['tasks']['alpha']['status']=='pending'
    if name=='retire_workspace' and case!='clean' and case!='remove_error': assert not any(x[:2]==['worktree','remove'] for x in commands)
    if case=='git_error':assert not bindings
    if case=='remove_error':assert bindings['alpha']['status']=='ready'

if __name__=='__main__':
    count=0
    for name,cases in CASES.items():
        for case in cases:
            ctx=fixture_context(name,case);env={};exec(ctx['setup'],env);exec(inspect.getsource(next(f for f in FUNCTIONS if f.__name__==name)),env);exec(ctx['entry'],env);check(name,case,env);count+=1
    print('PASS',count,'same-source teaching bindings; Git/task reads are explicit substitutes')
