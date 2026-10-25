from types import SimpleNamespace
from app.runs.query_runner import QueryRunner


def test_actual_generation_history_contains_user_corrections_and_ineffective_results():
    runner=QueryRunner.__new__(QueryRunner)
    runner._recent_messages=lambda user,current:[{'role':'assistant','text':'原有答案'}]
    support={'context_version':3,'slots':{'device':{'value':'AX-25','confirmed':True,'source':'user_report'},
        'environment':{'value':'猜测环境','confirmed':False,'source':'unconfirmed'}},
        'operations':[{'suggestion':'检查电源','status':'ineffective','reports':[{'note':'无效且请勿重复','source':'user_report'}]}]}
    history=runner._history(None,{'support_snapshot':support})
    assert 'AX-25' in str(history) and '无效且请勿重复' in str(history)
    assert '猜测环境' not in str(history)
    assert history[0]['text']=='原有答案'
