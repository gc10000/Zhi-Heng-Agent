"""评测结果只带公开型号选择字段，不传递内部Run或租约内容。"""
from app.knowledge.repository import fingerprint


CHAT_COMPONENT = 'frontend/src/features/chat/components/ProductClarification.vue'
CHAT_SHA256 = 'e336c172351bdefe42a03543ab12764ff87e7e517c4a597f647ba46d0090001b'
REVIEW_COMPONENT = 'frontend/src/features/evaluation/ResultPresentation.vue'
REVIEW_SHA256 = 'bba73261ebf64252eb769447c7f777d796770f6390cc9aa7338bc8fc0ba5b741'


def clarification_presentation_snapshot(candidates, products):
    """冻结澄清的产品显示、审核显示与对应前端源码身份。"""
    catalog = {row['product_id']: row for row in products if isinstance(row, dict) and row.get('product_id')}
    visible = []
    for candidate in public_candidates(candidates, catalog):
        product = catalog[candidate['product_id']]
        if candidate['model'] != product.get('model'):
            raise ValueError('澄清候选型号与冻结产品目录不一致')
        chat_candidate = dict(candidate)
        series = product.get('series')
        if isinstance(series, str) and series.strip():
            chat_candidate['series'] = series
        visible.append(chat_candidate)
    review_candidates = [dict(product_id=row['product_id'], model=row['model']) for row in visible]
    snapshot = dict(
        schema_version='clarification_presentation_v1',
        state='awaiting_input',
        behavior='clarify',
        chat=dict(
            heading='请选择适用型号',
            body='不同型号可能使用不同参数。确认后才会在对应资料中检索。',
            candidates=visible,
            source=dict(component=CHAT_COMPONENT, sha256=CHAT_SHA256),
        ),
        review=dict(
            state_line='运行状态：awaiting_input',
            heading='请选择适用型号',
            body='本轮请求确认设备型号，未生成答案。不同型号可能使用不同参数。确认后才会在对应资料中检索。',
            candidates=review_candidates,
            empty_candidates_note=(
                '本轮没有可展示的型号候选；需核对关联Run的只读材料，不能据此认定已选择具体型号。'
                if not review_candidates else None
            ),
            source=dict(component=REVIEW_COMPONENT, sha256=REVIEW_SHA256),
        ),
    )
    return snapshot | {'sha256': fingerprint(snapshot)}


def public_candidates(rows, authorized=None):
    allowed = set(authorized) if authorized is not None else None
    result = []
    seen = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        pid, model = row.get('product_id'), row.get('model')
        if (not isinstance(pid, str) or not pid or not isinstance(model, str) or not model or
                pid in seen or allowed is not None and pid not in allowed):
            continue
        seen.add(pid)
        result.append(dict(product_id=pid, model=model))
    return result


def validate_clarification_presentation_snapshot(snapshot, *, candidates, state, behavior):
    """写入与读取共用完整校验；历史缺快照的记录不走此分支。"""
    if not isinstance(snapshot, dict) or set(snapshot) != {
        'schema_version', 'state', 'behavior', 'chat', 'review', 'sha256',
    }:
        raise ValueError('澄清呈现快照结构无效')
    unsigned = {key: value for key, value in snapshot.items() if key != 'sha256'}
    if snapshot.get('sha256') != fingerprint(unsigned):
        raise ValueError('澄清呈现快照哈希不匹配')
    if (snapshot.get('schema_version') != 'clarification_presentation_v1' or
            snapshot.get('state') != 'awaiting_input' or state != 'awaiting_input' or
            snapshot.get('behavior') != 'clarify' or behavior != 'clarify'):
        raise ValueError('澄清呈现快照状态或版本不匹配')
    chat, review = snapshot.get('chat'), snapshot.get('review')
    if not isinstance(chat, dict) or not isinstance(review, dict):
        raise ValueError('澄清呈现快照字段无效')
    # 由同版本构造器重算文案、公开字段及产品/审核候选关系。
    products = chat.get('candidates')
    if not isinstance(products, list):
        raise ValueError('澄清呈现快照候选无效')
    expected = clarification_presentation_snapshot(candidates, products)
    # 历史快照保留当时源码身份；部署更新不以当前源码hash覆盖旧证据。
    import re
    for surface, component in (('chat', CHAT_COMPONENT), ('review', REVIEW_COMPONENT)):
        source = snapshot[surface].get('source')
        if (not isinstance(source, dict) or set(source) != {'component', 'sha256'} or
                source.get('component') != component or
                not isinstance(source.get('sha256'), str) or
                re.fullmatch(r'[0-9a-f]{64}', source['sha256']) is None):
            raise ValueError('澄清呈现快照源码身份无效')
        expected[surface]['source'] = source
    expected['sha256'] = fingerprint({key: value for key, value in expected.items() if key != 'sha256'})
    if expected != snapshot:
        raise ValueError('澄清呈现快照与结果或公开呈现不匹配')
    return snapshot
