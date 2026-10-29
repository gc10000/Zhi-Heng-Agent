"""输出分段不会越过图片授权边界。"""
import pytest
from app.runs.answer_filter import AnswerFilter


@pytest.mark.parametrize('parts,expected', [
    (['正文', '完成'], '正文完成'),
    (['![图', '](asset://a)'], '![图](/api/v1/assets/a)'),
    (['![图](/api/v1/assets/a)'], '![图](/api/v1/assets/a)'),
    (['![图](asset://other)'], '（图片未在授权来源中登记）'),
    (['![图](https://external.invalid/image)'], '（图片未在授权来源中登记）'),
    (['前文<im', 'g src="https://external.invalid">后文'], '前文\\<img src="https://external.invalid">后文'),
    (['前文![未结束'], '前文（图片语法未通过来源检查）'),
    (['![图][ref]\n[ref]: https://external.invalid'], '（图片语法未通过来源检查）\n[ref]: https://external.invalid'),
])
def test_filter_stream_and_final_are_identical(parts, expected):
    output = []
    guard = AnswerFilter({'a'}, output.append)
    for part in parts:
        guard.write(part)
    guard.write('', final=True)
    assert ''.join(output) == guard.answer == expected
