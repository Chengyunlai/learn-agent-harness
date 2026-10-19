"""第十一课：只重试模型请求；完整响应才交回原工具循环。"""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import random
import time

_path = Path(__file__).resolve().parents[2] / 's10-system-prompt/user_code/practice.py'
_spec = importlib.util.spec_from_file_location('s10_practice', _path)
# 以路径加载上一课，避免所有课的runtime同名互相覆盖。
_s10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s10)

class RecoveryStopped(RuntimeError):
    """恢复未取得完整响应；由旧循环作为model_error保留已有历史。"""


def classify_failure(outcome):
    """接收适配器的基本数据，不匹配任意SDK异常文字。"""
    if type(outcome) is not dict:
        return {'action': 'stop', 'reason': 'invalid_response'}
    if 'failure' in outcome:
        failure = outcome['failure']
        if type(failure) is not dict:
            return {'action': 'stop', 'reason': 'invalid_failure'}
        status = failure.get('status')
        if type(status) is int and status in (429, 500, 502, 503, 504, 529):
            return {'action': 'wait', 'reason': str(status), 'retry_after': failure.get('retry_after')}
        if failure.get('transport') in ('connection', 'timeout') and status is None:
            return {'action': 'wait', 'reason': failure['transport']}
        return {'action': 'stop', 'reason': 'request_error:' + str(status)}
    reason = outcome.get('stop_reason')
    if reason == 'max_tokens':
        return {'action': 'expand', 'reason': 'max_tokens'}
    if reason in ('end_turn', 'tool_use') and type(outcome.get('content')) is list and outcome['content']:
        return {'action': 'accept', 'reason': reason}
    return {'action': 'stop', 'reason': 'unsupported_response:' + str(reason)}


def retry_delay(attempt, retry_after=None, jitter=0.0):
    """优先有效秒数；无效/日期格式回退，过长等待由调用者停下而非缩短。"""
    if type(attempt) is not int or not 0 <= attempt < 4:
        raise ValueError('尝试序号必须在0到3之间。')
    if type(jitter) not in (int, float) or not math.isfinite(jitter) or not 0 <= jitter <= 1:
        raise ValueError('抖动比例必须在0到1之间。')
    seconds = None
    if type(retry_after) in (str, int, float):
        try:
            value = float(retry_after)
            if math.isfinite(value) and value >= 0:
                seconds = value
        except ValueError:
            pass
    if seconds is not None:
        return seconds
    base = min(0.25 * 2 ** attempt, 2.0)
    return base + base * 0.25 * jitter


def request_with_recovery(send, request, state, pause=time.sleep, random_unit=random.random):
    """每次逻辑请求最多4次尝试；父会话共享20次请求/3秒计划等待额度。"""
    checked_state(state)
    pending = deepcopy(request)
    if pending.get('max_tokens') != 1024 or type(pending.get('max_tokens')) is not int:
        raise ValueError('教学输出预算从1024开始。')
    expanded = False
    for attempt in range(1, 5):
        if state['remaining'] == 0:
            raise RecoveryStopped('request_budget')
        state['remaining'] -= 1
        outcome = send(deepcopy(pending))
        decision = classify_failure(outcome)
        state['events'].append({'attempt': attempt, 'action': decision['action'], 'reason': decision['reason']})
        if decision['action'] == 'accept':
            return outcome
        if decision['action'] == 'stop':
            raise RecoveryStopped(decision['reason'])
        if attempt == 4 or state['remaining'] == 0:
            raise RecoveryStopped('request_budget')
        if decision['action'] == 'expand':
            if expanded:
                raise RecoveryStopped('output_still_truncated')
            pending['max_tokens'] = 2048
            expanded = True
            continue
        delay = retry_delay(attempt - 1, decision.get('retry_after'), random_unit())
        if state['waited'] + delay > 3:
            raise RecoveryStopped('wait_budget')
        state['waited'] += delay
        state['events'][-1]['delay'] = delay
        pause(delay)
    raise RecoveryStopped('request_budget')


def checked_state(state):
    if type(state) is not dict or set(state) != {'remaining', 'waited', 'events'}:
        raise ValueError('恢复状态必须由宿主持有。')
    if type(state['remaining']) is not int or not 0 <= state['remaining'] <= 20 or type(state['waited']) not in (int, float) or not math.isfinite(state['waited']) or not 0 <= state['waited'] <= 3 or type(state['events']) is not list or len(state['events']) > 20:
        raise ValueError('请求或等待额度无效。')


def sdk_send(client, request):
    """固定SDK的类型化异常转成基本数据；400/413不凭错误文本猜压缩。"""
    from anthropic import APIStatusError, APIConnectionError, APITimeoutError
    try:
        response = client.messages.create(**request)
        return response.model_dump(mode='json', exclude_none=True)
    except APIStatusError as error:
        return {'failure': {'status': error.status_code, 'retry_after': error.response.headers.get('retry-after')}}
    except APITimeoutError:
        return {'failure': {'transport': 'timeout'}}
    except APIConnectionError:
        return {'failure': {'transport': 'connection'}}
