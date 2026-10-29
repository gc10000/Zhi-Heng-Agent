"""答案提示必须把产品机身与具名配件证据分开。"""
from app.answering.service import AnswerBudget
from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt


def test_prompt_preserves_named_accessory_scope_without_product_reselection():
    prompt = step_2_construct_prompt({
        'original_query': 'G540 扩展坞 USB-C 充电口有什么限制？',
        'item_names': ['华为擎云 G540'],
        'history': [],
        'answer_budget': AnswerBudget(context_window=4096, output_tokens=512, reserve_tokens=64, max_chars=3000),
        'reranked_docs': [
            {
                'chunk_uid': 'body-1', 'chunk_id': 'body-1', 'source': 'local', 'score': 0.9,
                'title': '华为擎云 G540/外观介绍/机身接口',
                'text': '机身 USB-C 接口支持数据传输。',
            },
            {
                'chunk_uid': 'dock-1', 'chunk_id': 'dock-1', 'source': 'local', 'score': 0.8,
                'title': '华为擎云 G540/配件及扩展连线/HUAWEI MateDock 3',
                'text': 'HUAWEI MateDock 3 的 USB-C 充电接口用于充电，不支持数据传输。',
            },
        ],
    })

    # The real prompt builder must carry both distinct evidence objects and their source names.
    assert '[title=华为擎云 G540/外观介绍/机身接口]' in prompt
    assert '[title=华为擎云 G540/配件及扩展连线/HUAWEI MateDock 3]' in prompt
    assert 'HUAWEI MateDock 3 的 USB-C 充电接口用于充电，不支持数据传输。' in prompt
    assert '华为擎云 G540' in prompt

    # Prompt contract: preserve the manual's exact accessory identity and avoid unsupported reselection.
    assert '具名配件' in prompt
    assert '保留其准确配件名称' in prompt
    assert '不得将配件规格归到机身或其他配件' in prompt
    assert '不得仅为确认已有证据明确指明的配件而要求重新选择型号' in prompt
