"""自制演示来源制作：仅移除明确的旧运行状态句，保留相邻全部产品原文。"""
from pathlib import Path
import argparse

STATUS_SENTENCE='本机预览禁用新增模型生成。'


def product_source(text):
    if text.count(STATUS_SENTENCE)!=1:
        raise ValueError('旧运行状态句缺失或不唯一，拒绝猜测删行')
    return text.replace(STATUS_SENTENCE,'',1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    value=product_source(Path(args.source).read_text('utf-8'))
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as f:
        f.write(value)
