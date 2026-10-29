"""最终输出必须保留技术文字；分段方式不能改变代码或授权结果。"""
import pytest
from html.parser import HTMLParser
from markdown_it import MarkdownIt

from app.runs.answer_filter import AnswerFilter


def filtered(text, size):
    output = []
    guard = AnswerFilter({'diagram'}, output.append)
    for start in range(0, len(text), size):
        guard.write(text[start:start + size])
    guard.write('', final=True)
    assert guard.answer == ''.join(output)
    return guard.answer


@pytest.mark.parametrize('size', [1, 2, 7, 10000])
@pytest.mark.parametrize('text', [
    '命令 `set address <ADDRESS>`，替换 `<ADDRESS>`。',
    '单击 `<应用设置>` 按钮。',
    '```text\n<DEVICE>system-view\nset address <ADDRESS>\n```',
    '``包含 ` 的 <input> 参数``。',
    '将 `![图](asset://untrusted)` 命令按原样粘贴。',
    '```markdown\n![图](asset://untrusted)\n```',
    '````text\n```\n<DEVICE>\n```\n````',
    '~~~text\n<DEVICE>\n~~~',
    '    <DEVICE>system-view\n    set address <ADDRESS>\n',
    '> ```text\n> <DEVICE>\n> ```',
    '- 示例：\n\n  ```text\n  <DEVICE>\n  ```',
    '```text\r\n<DEVICE>\r\n```',
    '命令 `<input>`，HTML示例 `<img src=x onerror=evil()>`。',
    '```text\n<DEVICE>\n\n<ADDRESS>\n```\n\n完成。',
])
def test_code_and_button_text_survives_stream_fragments(text, size):
    assert filtered(text, size) == text


@pytest.mark.parametrize('text', [
    '参数 <ADDRESS>，单击 <应用设置>。',
    '数值 1 < 2，未闭合 <ADDRESS',
    '<script>alert(1)</script><img src=x onerror=evil()><svg onload=evil()>',
    '前文 <img\nsrc=x onerror=evil()> 后文',
    '<!-- 注释 --> <iframe src=x>内容</iframe>',
    '未闭合反引号 ` 后有 <img src=x>。',
    '\\`<img src=x>\\`',
    '原样显示 \\<ADDRESS>，不显示额外反斜杠。',
    '# 未闭合 ` 标题\n\n<img src=x>\n\n另一段 `',
    '<div>\n\n```text\n<DEVICE>\n```\n\n</div>',
])
def test_prose_angles_render_as_text_and_cannot_create_html(text):
    parser = MarkdownIt('default', {'html': False, 'breaks': True})
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.value = ''
        def handle_data(self, value):
            self.value += value
    expected = Text(); expected.feed(parser.render(text))
    for size in (1, 2, 7, 10000):
        answer = filtered(text, size)
        visible = Text(); visible.feed(parser.render(answer))
        assert visible.value == expected.value
        # 即便额外以HTML开启的解析器消费，非代码HTML也只能显示为文字。
        rendered = MarkdownIt('default', {'html': True}).render(answer)
        assert '<script' not in rendered and '<img ' not in rendered
        assert '<svg' not in rendered and '<iframe' not in rendered


@pytest.mark.parametrize('size', [1, 2, 7, 10000])
def test_angle_text_and_authorized_images_keep_separate_boundaries(size):
    text = '单击 `<应用>`。![图](asset://diagram)\n\n<img src=x>![坏图](asset://other)'
    answer = filtered(text, size)
    assert '`<应用>`' in answer
    assert '![图](/api/v1/assets/diagram)' in answer
    assert '（图片未在授权来源中登记）' in answer
    assert r'\<img src=x>' in answer


def test_plain_stream_still_emits_before_final():
    output = []
    guard = AnswerFilter(set(), output.append)
    guard.write('正在回答。')
    assert ''.join(output) == '正在回答。'


def test_ordinary_exclamation_followed_by_text_does_not_hold_the_stream():
    output = []
    guard = AnswerFilter(set(), output.append)
    guard.write('收到!继续')
    assert ''.join(output) == '收到!继续'


def test_fenced_code_with_angle_prompts_streams_before_block_ends():
    output = []
    guard = AnswerFilter(set(), output.append)
    guard.write('```text\n')
    guard.write('<DEVICE>system-view\n')
    assert ''.join(output) == '```text\n<DEVICE>system-view\n'


def test_every_two_part_split_preserves_code_and_image_decisions():
    text = '参数 ``<ADDRESS>``。\n\n![图](asset://diagram)\n\n<img src=x>'
    expected = '参数 ``<ADDRESS>``。\n\n![图](/api/v1/assets/diagram)\n\n\\<img src=x>'
    for cut in range(len(text) + 1):
        guard = AnswerFilter({'diagram'}, lambda text: None)
        guard.write(text[:cut])
        guard.write(text[cut:])
        guard.write('', final=True)
        assert guard.answer == expected
