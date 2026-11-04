"""运行状态与同一行产品事实分离，不能按整行删资料。"""
from pathlib import Path
from scripts.operations.demo_source import product_source, STATUS_SENTENCE


def test_status_sentence_does_not_remove_adjacent_fact():
    original='## 数据核对\n\n核对设备标识、当前修订和引用原文，再由用户决定后续操作。'+STATUS_SENTENCE+'\n'
    assert product_source(original)==original.replace(STATUS_SENTENCE,'')
    assert '核对设备标识、当前修订和引用原文' in product_source(original)


def test_versioned_example_preserves_every_product_character():
    root=Path(__file__).resolve().parents[2]
    original=(root/'examples/preview/manual.md').read_text('utf-8')
    fixed=(root/'examples/preview/manual-operational-v1.md').read_text('utf-8')
    assert fixed==product_source(original)
    assert all(fact in fixed for fact in ['一个演示网口','属于配件','操作前先断电','亮起后再松开','当前修订和引用原文'])
