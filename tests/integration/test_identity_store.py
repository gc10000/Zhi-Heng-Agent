"""真实独立Mongo验证限流跨实例、过期及会话撤销。"""
from uuid import uuid4
import pytest
pytestmark = pytest.mark.integration


def test_sessions_and_limits_survive_service_restart(mongo_db):
    from app.identity.service import IdentityService, MongoIdentityStore, digest
    from app.api.errors import APIError
    name = uuid4().hex
    service = IdentityService(MongoIdentityStore(mongo_db))
    user = service.add_user(name, 'independent-password', role='maintainer', kb_ids=['test'])
    token, principal = service.login(name, 'independent-password', name)
    restarted = IdentityService(MongoIdentityStore(mongo_db))
    assert restarted.authenticate(token) == user == principal
    saved = mongo_db.login_sessions.find_one({'_id': digest(token)})
    assert saved and token not in repr(saved)
    restarted.logout(token)
    with pytest.raises(APIError):
        service.authenticate(token)
    for _ in range(9):
        restarted.login(name, 'independent-password', name)
    with pytest.raises(APIError) as limited:
        service.login(name, 'independent-password', name)
    assert limited.value.status == 429
