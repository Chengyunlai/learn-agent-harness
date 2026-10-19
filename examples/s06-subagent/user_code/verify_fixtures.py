"""对相同公开绑定运行完整函数，检查无真实文件/模型调用的教学路径。"""
import inspect
from figure_fixtures import FUNCTIONS,CASES,fixture_context
for function in FUNCTIONS:
    for case in CASES[function.__name__]:
        context=fixture_context(function.__name__,case);scope={}
        exec(context['setup'],scope);exec(inspect.getsource(function),scope);exec(context['entry'],scope)
        value=scope['observed']
        if case in ('missing','invalid'):assert 'error' in value
        elif function.__name__=='child_tools':assert set(value)=={'read_file'}
        elif function.__name__=='task_result':assert value['tool_use_id']=='parent_task_1' and value['is_error']==(case!='answered')
        elif case=='limit':assert value['status']=='call_limit'
        elif case=='forbidden':assert '未执行' in value['text']
print('PASS 9 teaching bindings, original function bodies')
