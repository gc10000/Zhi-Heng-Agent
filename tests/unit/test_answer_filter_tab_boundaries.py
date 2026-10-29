"""列表缩进展开后的原文保护；实际正文图片仍须走授权。"""
import pytest
from markdown_it import MarkdownIt

from app.runs.answer_filter import AnswerFilter


def filtered(parts):
    guard = AnswerFilter({'diagram'}, lambda text: None)
    for part in parts:
        guard.write(part)
    guard.write('', final=True)
    return guard.answer


@pytest.mark.parametrize('source', [
    '- `first\n\t<ADDRESS> ![example](asset://other)`',
    '- `first\n \t<ADDRESS> ![example](asset://other)`',
    '- `first\n  \t<ADDRESS> ![example](asset://other)`',
    '- `first\n\t\t<ADDRESS> ![example](asset://other)`',
    '1. `first\n\t<ADDRESS> ![example](asset://other)`',
    '10. `first\n\t <ADDRESS> ![example](asset://other)`',
    '- - `first\n\t\t<ADDRESS> ![example](asset://other)`',
    '> - `first\n> \t<ADDRESS> ![example](asset://other)`',
    '> > - `first\n> > \t<ADDRESS> ![example](asset://other)`',
    '- ``first `\n\t<ADDRESS> ![example](asset://other)``',
    '- `中文\r\n\t<ADDRESS> ![example](asset://other)`',
    '- `first\r\t<ADDRESS> ![example](asset://other)`',
    '- `first\n\t<ADDRESS> ![example](asset://other)`\n  ---',
])
def test_tab_container_code_preserves_source_for_every_split(source):
    md = MarkdownIt('default', {'html': False})
    assert any(c.type == 'code_inline' and '<ADDRESS>' in c.content
               for t in md.parse(source) for c in t.children or [])
    assert filtered(list(source)) == source
    for split in range(len(source) + 1):
        assert filtered([source[:split], source[split:]]) == source


@pytest.mark.parametrize('source, expected', [
    ('- first\n\t![bad](asset://other)', '- first\n\t（图片未在授权来源中登记）'),
    ('> - first\n> \t![bad](https://external.invalid/img)', '> - first\n> \t（图片未在授权来源中登记）'),
    ('- first\n\t![ok](asset://diagram)', '- first\n\t![ok](/api/v1/assets/diagram)'),
    ('- first\n\t<img src=x>', '- first\n\t\\<img src=x>'),
    ('- | A | B |\n  |---|---|\n\t| `x | ![bad](asset://other)` |',
     '- | A | B |\n  |---|---|\n\t| `x | （图片未在授权来源中登记）` |'),
    ('- `first\n\t<ADDRESS>` ![bad](asset://other)',
     '- `first\n\t<ADDRESS>` （图片未在授权来源中登记）'),
])
def test_tab_container_does_not_exempt_real_images_or_html(source, expected):
    assert filtered(list(source)) == expected
    for split in range(len(source) + 1):
        assert filtered([source[:split], source[split:]]) == expected
