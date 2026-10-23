"""显式派发/核对Mongo导入任务；broker只有job_id，不传本机路径。"""
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


async def run(once):
    from app.settings import Settings
    from app.main import open_resources
    from app.ingestion.jobs import JobRepository
    from app.ingestion.dispatcher import Dispatcher
    settings = Settings.load()
    if not os.getenv('REDIS_URL'):
        raise ValueError('请在根目录.env配置REDIS_URL，用于派发导入任务。')
    from app.infrastructure.queue.celery_app import celery_app
    async with open_resources(settings) as resources:
        dispatcher = Dispatcher(JobRepository(resources['db']),
            lambda jid: celery_app.send_task('knowledge.import', args=[jid]))
        while True:
            count = await asyncio.to_thread(dispatcher.dispatch)
            print('本次派发任务数=' + str(count), flush=True)
            if once:
                return
            await asyncio.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    try:
        asyncio.run(run(args.once))
    except Exception as exc:
        print('任务派发失败，异常类型=' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
