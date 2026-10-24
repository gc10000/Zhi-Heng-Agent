"""引用以run中的不可变入选快照回看，不能通过任意chunkID读取其他资料。"""
import re
from fastapi import APIRouter, Depends, Request
from app.api.errors import APIError
from app.identity.api import principal
from app.knowledge.api import gateway
from app.knowledge.asset_api import asset_record

router = APIRouter(prefix='/api/v1', tags=['引用'])


def controlled_markdown(text, allowed_assets):
    def replace(match):
        target = match.group(2)
        if target.startswith('asset://') and target[8:] in allowed_assets:
            return '![' + match.group(1) + '](/api/v1/assets/' + target[8:] + ')'
        return '（图片未在授权来源中登记）'
    return re.sub(r'!\[([^\]]*)\]\(([^\n)]*)\)', replace, text)


@router.get('/runs/{rid}/citations/{cid}')
def citation(rid: str, cid: str, request: Request, user=Depends(principal)):
    run = request.app.state.resources['runs'].get(user, rid)
    selected = next((c for c in run['citations'] if c['citation_id'] == cid), None)
    if selected is None:
        raise APIError(404, 'not_found', '本轮没有此引用。')
    g = gateway(request)
    g.revision(user, selected['document_id'], selected['revision_id'])
    assets = selected.get('asset_ids', [])
    for aid in assets:
        row, _ = asset_record(g, user, aid)
        if row['revision_id'] != selected['revision_id']:
            raise APIError(404, 'not_found', '引用图片不属于此修订。')
    # 只读精确修订登记的原件，不让浏览器推导稳定ID，也不返回存储对象键。
    original = g.db.knowledge_original_assets.find_one({'document_id': selected['document_id'], 'revision_id': selected['revision_id']})
    descriptor = None
    if original is not None:
        asset_record(g, user, original['asset_id'])
        descriptor = {k: original[k] for k in ('asset_id', 'media_type', 'name')}
        descriptor['url'] = '/api/v1/assets/' + original['asset_id']
    return selected | {'display_text': controlled_markdown(selected.get('text', ''), set(assets)),
                       'asset_urls': {aid: '/api/v1/assets/' + aid for aid in assets}, 'original': descriptor}
