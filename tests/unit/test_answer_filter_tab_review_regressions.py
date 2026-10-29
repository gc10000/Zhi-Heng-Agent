"""本轮独立合成反例：Markdown列表制表符展开不得损坏代码。"""
import pytest
from markdown_it import MarkdownIt
from app.runs.answer_filter import AnswerFilter


def output(source, size):
    guard = AnswerFilter({'diagram'}, lambda text: None)
    for i in range(0, len(source), size):
        guard.write(source[i:i+size])
    guard.write('', final=True)
    return guard.answer


@pytest.mark.parametrize('body', ['<ADDRESS>', '![example](asset://other)'])
def test_tab_expanded_list_code_preserves_literal_text(body):
    source = '- `first\n\t' + body + '`'
    # 由真实Markdown块及行内解析确认它是合法code_inline，而非正文图片。
    md = MarkdownIt('default', {'html': False})
    inline = next(t for t in md.parse(source) if t.type == 'inline')
    assert any(t.type == 'code_inline' and body in t.content for t in inline.children)
    for size in (len(source), 1, 2, 7):
        assert output(source, size) == source


def test_equivalent_space_indentation_preserves_code():
    source = '- `first\n    <ADDRESS> ![example](asset://other)`'
    assert output(source, 1) == source


def test_list_tab_after_marker_and_continuation_preserves_code():
    source = '-\t`first\n\t<ADDRESS> ![example](asset://other)`'
    assert output(source, 1) == source
