"""生成失败必须跨越节点边界传播；部分文本不能当作成功答案。"""


class AnswerGenerationError(RuntimeError):
    def __init__(self, message='回答生成失败，请稍后重试。', partial_answer=''):
        super().__init__(message)
        self.partial_answer = partial_answer
