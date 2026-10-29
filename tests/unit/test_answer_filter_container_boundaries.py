"""AF-R1/AF-R2：容器内代码、图片授权及围栏流分段的一致性。"""
import pytest

from app.runs.answer_filter import AnswerFilter


def output(parts):
    guard = AnswerFilter({'diagram'}, lambda text: None)
    for part in parts:
        guard.write(part)
    guard.write('', final=True)
    return guard.answer


@pytest.mark.parametrize('source,expected', [
    ('| A | B |\n|---|---|\n| `x | ![image](asset://diagram)` |',
     '| A | B |\n|---|---|\n| `x | ![image](/api/v1/assets/diagram)` |'),
    ('| `x | ![image](asset://other)` |\n|---|---|\n| a | b |',
     '| `x | （图片未在授权来源中登记）` |\n|---|---|\n| a | b |'),
    ('> | A | B |\n> |---|---|\n> | `x | ![image](https://external.invalid/img)` |',
     '> | A | B |\n> |---|---|\n> | `x | （图片未在授权来源中登记）` |'),
    ('| A | B |\n|---|---|\n| `x | <img src=x>` |',
     '| A | B |\n|---|---|\n| `x | \\<img src=x>` |'),
    ('| A | B |\r\n|---|---|\r\n| `x | ![image](asset://other)` |',
     '| A | B |\r\n|---|---|\r\n| `x | （图片未在授权来源中登记）` |'),
])
def test_table_authorization_uses_real_cells_for_all_splits(source, expected):
    assert output(list(source)) == expected
    for split in range(len(source) + 1):
        assert output([source[:split], source[split:]]) == expected


@pytest.mark.parametrize('source', [
    '| A | B |\n|---|---|\n| `<ADDRESS>` | `![image](asset://other)` |',
    '| A | B |\n|---|---|\n| ``a ` <ADDRESS>`` | `![image](asset://other)` |',
    '| A | B |\n|---|---|\n| `x\\|<ADDRESS>` | `![image](asset://other)` |',
    '| A | B |\n|---|---|\n| `<ADDRESS>` | `<ADDRESS>` |',
    '> | A | B |\n> |---|---|\n> | `<ADDRESS>` | `![image](asset://other)` |',
    '- | A | B |\n  |---|---|\n  | `<ADDRESS>` | `![image](asset://other)` |',
    '> `first\n> <ADDRESS> ![example](asset://other)`',
    '- `first\n  <ADDRESS> ![example](asset://other)`',
])
def test_real_container_code_is_preserved(source):
    for size in (1, 2, 7, len(source)):
        assert output([source[i:i + size] for i in range(0, len(source), size)]) == source


@pytest.mark.parametrize('target,expected', [
    ('asset://other', '（图片未在授权来源中登记）'),
    ('https://external.invalid/img', '（图片未在授权来源中登记）'),
    ('asset://diagram', '![image](/api/v1/assets/diagram)'),
])
def test_incomplete_fence_info_all_splits_have_same_authorization(target, expected):
    source = '```x ![image](' + target + ')`\n'
    answer = '```x ' + expected + '`\n'
    assert output(list(source)) == answer
    for split in range(len(source) + 1):
        assert output([source[:split], source[split:]]) == answer


@pytest.mark.parametrize('source', [
    '````text\n```\n![image](asset://other) <ADDRESS>\n````\n',
    '~~~text\n![image](asset://other) <ADDRESS>\n~~~\n',
    '> ````text\r\n> ![image](asset://other) <ADDRESS>\r\n> ````\r\n',
])
def test_valid_complete_fences_remain_literal_for_every_split(source):
    assert output(list(source)) == source
    for split in range(len(source) + 1):
        assert output([source[:split], source[split:]]) == source


def test_fence_info_is_held_until_newline_and_body_still_streams():
    sent = []
    guard = AnswerFilter({'diagram'}, sent.append)
    guard.write('```text ![example](asset://other)')
    assert 'asset://other' not in ''.join(sent)
    guard.write('\n')
    guard.write('<ADDRESS> ![example](asset://other)\n')
    assert ''.join(sent) == '```text ![example](asset://other)\n<ADDRESS> ![example](asset://other)\n'
