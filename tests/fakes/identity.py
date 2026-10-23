"""身份端口的离线存储；业务密码和会话逻辑仍调用真实服务。"""
import copy


class IdentityStore:
    def __init__(self):
        self.users, self.sessions, self.attempts = {}, {}, {}

    def user(self, username):
        user = self.users.get(username)
        return copy.deepcopy(user) if user and user['enabled'] else None

    def add_user(self, data):
        assert data['username'] not in self.users
        self.users[data['username']] = copy.deepcopy(data)

    def consume(self, key, now):
        slot = key, int(now.timestamp()) // 300
        self.attempts[slot] = self.attempts.get(slot, 0) + 1
        return self.attempts[slot] <= 10

    def save_session(self, data):
        self.sessions[data['_id']] = copy.deepcopy(data)

    def session(self, key, now):
        value = self.sessions.get(key)
        return copy.deepcopy(value) if value and not value['revoked'] and value['expires_at'] > now else None

    def revoke(self, key):
        if key in self.sessions:
            self.sessions[key]['revoked'] = True
