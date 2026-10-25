"""统一API工厂；导入不连接存储、不加载模型、不修改桶策略。"""
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from app.api.errors import install
from app.settings import Settings


@asynccontextmanager
async def open_resources(settings):
    from pymongo import MongoClient
    client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000, tz_aware=True)
    try:
        client.admin.command('ping')
        from app.identity.service import IdentityService, MongoIdentityStore
        from app.conversations.repository import ConversationRepository
        from app.runs.repository import RunRepository
        from app.runs.service import RunService
        from app.runs.events import EventLedger
        from app.runs.commands import RunCommands
        from app.knowledge.resources import KnowledgeResources
        db = client[settings.database]
        conversations = ConversationRepository(db)
        runs = RunRepository(db, conversations)
        events = EventLedger(runs)
        commands = RunCommands(runs, events, lease_seconds=settings.run_lease_seconds,
                               input_wait_seconds=settings.input_wait_seconds, pending_seconds=settings.run_pending_seconds)
        knowledge = KnowledgeResources(db, settings)
        from app.runs.query_runner import QueryRunner
        query_runner = QueryRunner(runs, commands, knowledge.get, identity_store=MongoIdentityStore(db))
        try:
            yield {'db': db, 'identity': IdentityService(MongoIdentityStore(db), session_seconds=settings.session_seconds),
                   'conversations': conversations, 'runs': runs, 'run_service': RunService(runs),
                   'events': events, 'commands': commands, 'knowledge': knowledge.get, 'query_runner': query_runner}
        finally:
            query_runner.close()
            knowledge.close()
    finally:
        client.close()


def create_app(*, settings=None, resource_factory=open_resources):
    @asynccontextmanager
    async def lifespan(application):
        application.state.ready = False
        configured = settings if settings is not None else Settings.load()
        application.state.settings = configured
        async with resource_factory(configured) as resources:
            import asyncio
            import logging
            async def recovery_loop():
                while True:
                    try:
                        await asyncio.to_thread(resources['commands'].recover)
                    except Exception as exc:
                        logging.getLogger(__name__).error('运行恢复扫描失败，异常类型：%s', type(exc).__name__)
                    await asyncio.sleep(10)
            recovery = asyncio.create_task(recovery_loop()) if 'commands' in resources else None
            async def query_loop():
                while True:
                    try:
                        await asyncio.to_thread(resources['query_runner'].scan)
                    except Exception as exc:
                        logging.getLogger(__name__).error('问答派发失败，异常类型：%s', type(exc).__name__)
                    await asyncio.sleep(.2)
            query = asyncio.create_task(query_loop()) if 'query_runner' in resources else None
            application.state.resources = resources
            application.state.ready = True
            try:
                yield
            finally:
                application.state.ready = False
                if query:
                    query.cancel()
                    try:
                        await query
                    except asyncio.CancelledError:
                        pass
                if recovery:
                    recovery.cancel()
                    try:
                        await recovery
                    except asyncio.CancelledError:
                        pass

    application = FastAPI(title='设备技术支持与知识工作台', version='1.0.0', lifespan=lifespan)
    install(application)
    from app.identity.api import router as identity_router
    application.include_router(identity_router)
    from app.conversations.api import router as conversation_router
    application.include_router(conversation_router)
    from app.runs.api import router as run_router
    application.include_router(run_router)
    from app.knowledge.api import router as knowledge_router
    application.include_router(knowledge_router)
    from app.knowledge.asset_api import router as asset_router
    from app.knowledge.citation_api import router as citation_router
    application.include_router(asset_router)
    application.include_router(citation_router)
    from app.support.api import router as support_router
    application.include_router(support_router)

    @application.middleware('http')
    async def request_identity(request: Request, call_next):
        request.state.request_id = str(uuid4())
        result = await call_next(request)
        result.headers['X-Request-ID'] = request.state.request_id
        result.headers['X-Content-Type-Options'] = 'nosniff'
        return result

    @application.get('/api/v1/health', tags=['服务'])
    def health(request: Request):
        return {'ready': request.app.state.ready, 'version': 'v1'}

    return application


app = create_app()
