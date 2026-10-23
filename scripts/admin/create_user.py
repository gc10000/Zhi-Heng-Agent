"""本机管理员创建账号；密码交互输入，不放命令行/日志。"""
import argparse
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', required=True)
    parser.add_argument('--role', choices=['viewer', 'maintainer', 'admin'], required=True)
    parser.add_argument('--kb', action='append', required=True)
    args = parser.parse_args()
    from app.settings import Settings
    from app.identity.service import IdentityService, MongoIdentityStore
    from pymongo import MongoClient
    configured = Settings.load()
    password = getpass.getpass('新密码（至少12字符）：')
    if getpass.getpass('再次输入密码：') != password:
        parser.error('两次密码不一致。')
    with MongoClient(configured.mongo_url, serverSelectionTimeoutMS=5000) as client:
        user = IdentityService(MongoIdentityStore(client[configured.database])).add_user(
            args.username, password, role=args.role, kb_ids=args.kb)
        print('账号已创建，user_id=' + user.user_id)


if __name__ == '__main__':
    main()
