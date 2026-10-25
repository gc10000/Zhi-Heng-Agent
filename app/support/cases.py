"""处理草稿快照、用户编辑和确认；幂等重生成不覆盖用户内容。"""
from copy import deepcopy
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.models import stable_id
from app.conversations.repository import public
from .repository import now


class CaseRepository:
    def __init__(self, support):
        self.support = support
        self.collection = support.conversations.db.support_cases
        self.collection.create_index('case_id', unique=True)
        self.collection.create_index([('owner_id', 1), ('kb_id', 1), ('case_id', 1)])

    def get(self, user, case_id):
        row = self.collection.find_one(self.support.conversations.scope(user) | {'case_id': case_id})
        if row is None:
            raise APIError(404, 'not_found', '处理记录不存在或不在授权范围。')
        self.support.conversations.get(user, row['conversation_id'])
        return public(row)

    def create(self, user, data):
        run = self.support.runs.get(user, data.run_id)
        self.support.completed_run(user, run['conversation_id'], data.run_id)
        case_id = stable_id('case', user.user_id, [run['run_id']])
        if self.collection.find_one({'case_id': case_id}):
            return self.get(user, case_id)
        context = self.support.get(user, run['conversation_id'])
        if context['version'] != data.expected_support_version:
            raise APIError(409, 'version_conflict', '支持上下文已改变，请刷新后生成草稿。')
        fields = {key: value['value'] if value['confirmed'] and value['value'] else '未知' for key, value in context['slots'].items()}
        if fields['question'] == '未知':
            fields['question'] = run['question']
        fields.update(summary=run.get('answer', '') or '未知', handoff_reason=context.get('reason', '未知'))
        citations = deepcopy(run.get('citations', []))
        for step in context['operations']:
            for citation in step['citations']:
                if citation not in citations:
                    citations.append(deepcopy(citation))
        row = {'case_id': case_id, 'owner_id': user.user_id, 'kb_id': run['kb_id'],
            'conversation_id': run['conversation_id'], 'run_id': run['run_id'], 'status': 'draft', 'version': 0,
            'created_at': now(), 'fields': fields, 'context_snapshot': context,
            'run_snapshot': {k: deepcopy(run.get(k)) for k in ('run_id','question','answer','product_snapshot','citations')},
            'operations': deepcopy(context['operations']), 'citations': citations, 'edits': [], 'confirmed_at': None}
        try:
            self.collection.insert_one(row)
        except DuplicateKeyError:
            pass
        return self.get(user, case_id)

    def patch(self, user, case_id, data):
        current = self.get(user, case_id)
        if any(not value.strip() or len(value) > 16000 for value in data.fields.values()):
            raise APIError(422, 'invalid_case_fields', '字段不能为空且最多16000字；未知请明确填写未知。')
        changes = {key: value.strip() for key, value in data.fields.items()}
        return self._change(user, current, data.expected_version, {'fields': current['fields'] | changes},
            edit={'fields': changes, 'source': 'user_edit', 'recorded_at': now()})

    def confirm(self, user, case_id, version):
        current = self.get(user, case_id)
        if current['status'] == 'confirmed' and current.get('confirmation_version') == version:
            return current
        return self._change(user, current, version, {'status': 'confirmed', 'confirmed_at': now(), 'confirmation_version': version})

    def _change(self, user, current, version, fields, edit=None):
        update = {'$set': fields, '$inc': {'version': 1}}
        if edit:
            update['$push'] = {'edits': edit}
        row = self.collection.find_one_and_update(self.support.conversations.scope(user) | {
            'case_id': current['case_id'], 'version': version, 'status': 'draft'}, update, return_document=ReturnDocument.AFTER)
        if row is None:
            raise APIError(409, 'version_conflict', '记录已改变或已确认，请刷新；确认快照不能覆盖。')
        return public(row)

    def list(self, user, cursor=None, limit=50):
        query = self.support.conversations.scope(user)
        if cursor:
            query['case_id'] = {'$gt': cursor}
        rows = list(self.collection.find(query).sort('case_id', 1).limit(limit + 1))
        return {'items': [self.get(user, row['case_id']) for row in rows[:limit]],
                'next_cursor': rows[limit-1]['case_id'] if len(rows) > limit else None}
