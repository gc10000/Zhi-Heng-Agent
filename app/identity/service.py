"""单组织身份：scrypt密码、仅存摘要的可撤销会话与Mongo原子限流。"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from uuid import uuid4
from pymongo import ReturnDocument
from app.api.errors import APIError
from app.identity.models import Principal


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    if not 12 <= len(password) <= 1024:
        raise ValueError('密码长度需为12至1024字符。')
    salt = secrets.token_bytes(16)
    hashed = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return 'scrypt$16384$8$1$' + salt.hex() + '$' + hashed.hex()


def verify_password(password, encoded):
    try:
        name, n, r, p, salt, expected = encoded.split('$')
        if (name, n, r, p) != ('scrypt', '16384', '8', '1'):
            return False
        value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(value, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


class MongoIdentityStore:
    def __init__(self, db):
        self.users, self.sessions, self.attempts = db.users, db.login_sessions, db.login_attempts
        self.users.create_index('username', unique=True)
        self.users.create_index('user_id', unique=True)
        self.sessions.create_index('expires_at', expireAfterSeconds=0)
        self.attempts.create_index('expires_at', expireAfterSeconds=0)

    def user(self, username):
        return self.users.find_one({'username': username, 'enabled': True})

    def add_user(self, data):
        self.users.insert_one(data)

    def consume(self, key, now):
        window = int(now.timestamp()) // 300
        row = self.attempts.find_one_and_update({'_id': key + ':' + str(window)},
            {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': now + timedelta(minutes=10)}},
            upsert=True, return_document=ReturnDocument.AFTER)
        return row['count'] <= 10

    def save_session(self, data):
        self.sessions.insert_one(data)

    def session(self, key, now):
        return self.sessions.find_one({'_id': key, 'expires_at': {'$gt': now}, 'revoked': False})

    def revoke(self, key):
        self.sessions.update_one({'_id': key}, {'$set': {'revoked': True}})


class IdentityService:
    def __init__(self, store, *, session_seconds=28800, clock=None):
        self.store, self.session_seconds = store, session_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        # 未知用户也做相同成本校验，避免直接按用户名分支返回。
        self.dummy = hash_password(secrets.token_urlsafe(32))

    def add_user(self, username, password, *, role, kb_ids):
        public = Principal(user_id=str(uuid4()), username=username, role=role, kb_ids=tuple(kb_ids))
        self.store.add_user(public.model_dump(mode='json') | {'password_hash': hash_password(password), 'enabled': True})
        return public

    def login(self, username, password, remote):
        now = self.clock()
        if not self.store.consume(digest('remote:' + remote), now):
            raise APIError(429, 'login_rate_limited', '登录尝试过于频繁，请稍后再试。')
        user = self.store.user(username)
        valid = verify_password(password, user['password_hash'] if user else self.dummy)
        if not user or not valid:
            raise APIError(401, 'invalid_credentials', '用户名或密码错误。')
        token = secrets.token_urlsafe(32)
        self.store.save_session({'_id': digest(token), 'username': username, 'user_id': user['user_id'],
                                 'expires_at': now + timedelta(seconds=self.session_seconds), 'revoked': False})
        return token, self.principal(user)

    @staticmethod
    def principal(user):
        return Principal(**{k: user[k] for k in Principal.model_fields})

    def authenticate(self, token):
        saved = self.store.session(digest(token), self.clock()) if token else None
        user = self.store.user(saved['username']) if saved else None
        if user is None or user['user_id'] != saved['user_id']:
            raise APIError(401, 'authentication_required', '请重新登录。')
        return self.principal(user)

    def logout(self, token):
        self.store.revoke(digest(token))

    @staticmethod
    def csrf(token):
        return digest('csrf:' + token)
