"""真实隔离API/Redis/Linux/宿主失败传播；不调用模型，不将该探针当真实评测成功。"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'output') or output.exists():
        parser.error('必须选择output下全新证据目录，不能覆盖已有报告')
    output.mkdir(parents=True)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    from app.evaluation.validate_dataset import fingerprint, file_sha
    from app.identity.service import IdentityService, MongoIdentityStore
    from pymongo import MongoClient
    from scripts.verification.m2_live_api import api_process, wait_for
    import requests
    tag = uuid4().hex
    database, queue = 'm1_test_m6_queue_'+tag, 'm6-test-'+tag
    rows = [dict(id=f'probe-{i:03}', category='parameter', group_id=f'g{i}', split='dev',
        question=f'合成传输探针{i}：设备参数是什么？', product_names=['合成设备'], history=[],
        expected=dict(behavior='answer', key_points=['合成值'], forbidden_claims=[]),
        allowed_evidence=[[dict(document_sha256='a'*64, page=1, quote='合成值')]],
        source_scope=['a'*64], annotation=dict(method='source_checked_assistant_draft', status='draft'))
        for i in range(50)]
    data = output/'dataset.jsonl'
    data.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')
    manifest = output/'split.json'
    manifest.write_text(json.dumps(dict(version='probe',dataset_sha256=file_sha(data),
        rows=[dict(id=r['id'],split=r['split'],group_id=r['group_id'],sha256=fingerprint(r)) for r in rows],
        sources=[dict(sha256='a'*64,pages=1)],annotation_notice='合成传输测试草稿，不是真实评测标签')),encoding='utf-8')
    config = dict(experiment_id='transport-probe', phase='development', split='dev',
        execution_mode='real_query_runner', strategy='m3-baseline', metric_schema_version=1, seed=11,
        dataset_sha256=file_sha(data), split_manifest_sha256=file_sha(manifest),
        versions=dict(code='not-a-real-version',model='not-a-real-version',prompt='not-a-real-version'),
        target=dict(database='m1_test_m4_transport_'+tag,collection='m1_test_m4_transport_'+tag,
                    owner_id='m4-test-'+tag,kb_id='m4-test-'+tag,object_prefix='m4-test/'+tag+'/',bucket='probe-not-read'),
        corpus=dict(documents=[]))
    # 故意缺少完整语料快照：正式执行器必须在资源/模型构造前拒绝。
    (output/'config.json').write_text(json.dumps(config),encoding='utf-8')
    catalog = output/'catalog.json'
    catalog.write_text(json.dumps(dict(datasets=[dict(id='transport-probe',version='v1',dataset='dataset.jsonl',
        manifest='split.json',kb_ids=['transport'])],configs=[dict(id='control',version='v1',path='config.json')])),encoding='utf-8')
    with socket.socket() as guard:
        guard.bind(('127.0.0.1',0)); port=guard.getsockname()[1]
    env = dict(os.environ)
    env.update(M2_DB_NAME=database, M6_QUEUE_NAME=queue, M6_EVALUATION_CATALOG=str(catalog),
        M6_EVALUATION_WORK_DIR=str(output/'results'), MODEL_HOST_TOKEN=secrets.token_urlsafe(32),
        MODEL_HOST_URL='http://127.0.0.1:'+str(port), API_ALLOWED_ORIGINS='http://testserver',
        API_COOKIE_SECURE='false', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    name, started = 'm6-test-worker-'+tag, False
    report = dict(passed=False,database=database,queue=queue,checks={},paid_calls=0,
                  scope='真实传输与预执行失败门禁；无成功模型评测、无heldout')
    with (output/'host.log').open('xb') as host_log:
        host = subprocess.Popen([sys.executable,'-m','uvicorn','app.infrastructure.model_host:app',
            '--host','0.0.0.0','--port',str(port)],cwd=ROOT,env=env,stdout=host_log,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            with requests.Session() as http:
                http.trust_env=False
                def ready():
                    if host.poll() is not None: raise RuntimeError('隔离模型宿主提前退出，见本机host.log')
                    try: return http.get(env['MODEL_HOST_URL']+'/health',headers={'X-Model-Token':env['MODEL_HOST_TOKEN']},timeout=1).status_code==200
                    except requests.RequestException: return False
                wait_for(ready,bool,timeout=45)
            container_env=env|dict(REDIS_URL='redis://redis:6379/0',MODEL_HOST_URL='http://host.docker.internal:'+str(port))
            command=['docker','run','-d','--name',name,'--network','product-knowledge-rag_default',
                '--add-host','host.docker.internal:host-gateway','--mount',
                'type=bind,source='+str(ROOT/'app')+',target=/workspace/app,readonly']
            for key in ('REDIS_URL','M6_QUEUE_NAME','MODEL_HOST_URL','MODEL_HOST_TOKEN'):
                command+=['--env',key]
            command+=['product-knowledge-worker:m2','celery','-A','app.infrastructure.queue.celery_app:celery_app',
                'worker','--loglevel=WARNING','--concurrency=1','-Q',queue]
            result=subprocess.run(command,cwd=ROOT,env=container_env,capture_output=True)
            if result.returncode: raise RuntimeError('隔离Linux worker启动失败，退出码='+str(result.returncode))
            started=True
            with MongoClient(env['MONGO_URL'],serverSelectionTimeoutMS=5000) as mongo:
                db=mongo[database]
                if db.list_collection_names(): raise ValueError('拒绝复用已有传输测试账本')
                identity=IdentityService(MongoIdentityStore(db))
                password=secrets.token_urlsafe(24)
                identity.add_user('probe',password,role='maintainer',kb_ids=['transport'])
                with api_process(env,'m6-'+tag) as (http,base):
                    response=http.post(base+'/api/v1/auth/login',headers={'Origin':'http://testserver'},
                                       json=dict(username='probe',password=password),timeout=5)
                    response.raise_for_status()
                    headers={'Origin':'http://testserver','X-CSRF-Token':response.json()['csrf_token']}
                    response=http.post(base+'/api/v1/eval-sets',headers=headers,
                                       json=dict(kb_id='transport',eval_set_id='transport-probe',version='v1'),timeout=5)
                    report['checks']['registered_via_http']=response.status_code==201
                    if response.status_code != 201:
                        raise RuntimeError('题集登记失败，安全错误码：'+response.json().get('error',{}).get('code','unknown'))
                    response=http.post(base+'/api/v1/experiments',headers=headers,json=dict(kb_id='transport',
                        eval_set_id='transport-probe',eval_set_version='v1',config_id='control',config_version='v1',
                        client_request_id=tag),timeout=5)
                    report['checks']['queued_via_http']=response.status_code==202
                    if response.status_code != 202:
                        raise RuntimeError('实验创建失败，安全错误码：'+response.json().get('error',{}).get('code','unknown'))
                    eid=response.json()['experiment_id']
                    def read(): return http.get(base+'/api/v1/experiments/'+eid,timeout=5).json()
                    row=wait_for(read,lambda r:r.get('state') in {'failed','completed','cancelled'},timeout=90)
                    report.update(experiment_id=eid,state=row['state'],attempt=row['attempt'],error=row.get('error'))
                    report['checks']['linux_consumed_once']=row['attempt']==1
                    report['checks']['failed_before_model']=row['state']=='failed' and row['retryable'] is False
                    report['checks']['no_success_results']=not db.evaluation_results.count_documents({})
                    report['checks']['released_own_budget']=db.evaluation_slots.find_one()['active_experiment_id'] is None
                    report['checks']['no_generated_run']=not db.runs.count_documents({})
                report['passed']=all(report['checks'].values())
        finally:
            if started:
                logs=subprocess.run(['docker','logs',name],capture_output=True)
                (output/'worker.log').write_bytes(logs.stdout+logs.stderr)
                subprocess.run(['docker','stop','--time','10',name],capture_output=True)
            host.terminate()
            try: host.wait(timeout=15)
            except subprocess.TimeoutExpired: host.kill();host.wait()
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'paid_calls':0},ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
