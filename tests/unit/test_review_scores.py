"""评分输入不能把布尔或浮点强制转换成分数，独立离线验证。"""
import pytest
from pydantic import ValidationError
from app.evaluation.reviews import Scores


@pytest.mark.parametrize('value', [True, False, 1.0, '2', -1, 3])
def test_score_requires_explicit_integer_or_unknown(value):
    with pytest.raises(ValidationError):
        Scores(factuality=value, citation_support=2, actionability='unknown', image_relevance='not_applicable')


def test_unknown_is_distinct_from_zero_and_not_applicable():
    scores = Scores(factuality=0, citation_support='unknown', actionability=2, image_relevance='not_applicable')
    assert scores.model_dump() == dict(factuality=0, citation_support='unknown', actionability=2, image_relevance='not_applicable')
