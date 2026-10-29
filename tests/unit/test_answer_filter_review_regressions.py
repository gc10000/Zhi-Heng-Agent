"""合成反例；仅验证过滤器，不代表真实答案质量。"""
from markdown_it import MarkdownIt
from app.runs.answer_filter import AnswerFilter


def filtered(parts):
    result = AnswerFilter({'diagram'}, lambda text: None)
    for part in parts:
        result.write(part)
    result.write('', final=True)
    return result.answer


def test_table_cells_do_not_share_inline_code_delimiters():
    source = '| A | B |\n|---|---|\n| `x | ![bad](asset://other)` |'
    # 与展示端相同的Markdown语法下，该位置确为图片，而非代码。
    assert '<img ' in MarkdownIt('default', {'html': False}).render(source)
    for size in (1, 2, 7, len(source)):
        answer = filtered([source[i:i + size] for i in range(0, len(source), size)])
        assert 'asset://other' not in answer
        assert '（图片未在授权来源中登记）' in answer


def test_incomplete_fence_opener_cannot_change_image_authorization():
    first = '```x ![image](asset://other)'
    last = '`\n'
    source = first + last
    assert '<img ' in MarkdownIt('default', {'html': False}).render(source)
    whole = filtered([source])
    assert 'asset://other' not in whole
    assert filtered([first, last]) == whole
    assert filtered(list(source)) == whole


def test_valid_code_examples_remain_literal():
    for source in ('`![example](asset://other) <ADDRESS>`',
                   '````text\n```\n![example](asset://other) <ADDRESS>\n````\n'):
        assert filtered(list(source)) == source


def test_ordinary_unregistered_images_are_rejected():
    assert filtered(list('![bad](asset://other)')) == '（图片未在授权来源中登记）'
