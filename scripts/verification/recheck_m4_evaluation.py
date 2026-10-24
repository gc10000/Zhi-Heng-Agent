"""只读核验显式M4真实问答实验；不建索引、不加载模型、不调用供应商。"""
import argparse
import json
import re
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def verify(config_path,output):
    import yaml
    from app.evaluation.validate_dataset import validate_dataset,file_sha,fingerprint
    from app.evaluation.runner import check_split
    from app.evaluation.readonly import open_frozen_corpus
    config=yaml.safe_load(config_path.read_text('utf-8'))
    dataset=Path('evals/datasets/support-v1-r2.jsonl')
    manifest=Path('evals/datasets/support-v1-r2-manifest.json')
    questions=validate_dataset(dataset,manifest=manifest)
    check_split(config,json.loads(manifest.read_text('utf-8')))
    selected=[q for q in questions if q['split']==config['split']]
    if (output/'.runner.lock').exists():raise ValueError('实验仍在运行')
    report=json.loads((output/'manifest.json').read_text('utf-8'))
    assert report['config']==config and report['config_sha256']==fingerprint(config)
    assert report['status']=='completed' and report['failed']==0
    assert report['selected_ids']==[q['id'] for q in selected]
    records=[json.loads(s) for s in (output/'results.jsonl').read_text('utf-8').splitlines()]
    latest={}
    for line in (output/'attempts.jsonl').read_text('utf-8').splitlines():
        r=json.loads(line);assert r['config_sha256']==fingerprint(config);latest[r['id']]=r
    assert [r['id'] for r in records]==[q['id'] for q in selected]
    assert latest=={r['id']:r for r in records} and all(r['status']=='completed' for r in records)
    assert len({r['result']['run_id'] for r in records})==len(records)
    states={};messages_count=0;generations=0;decoded_images=set()
    with open_frozen_corpus(config) as g:
        sources={d['document_id']:d for d in config['corpus']['documents']}
        indexed={r['chunk_uid']:r for d in sources.values() for r in g.index().revision_rows(g.repo(config['target']['kb_id']),d['revision_id'])}
        for q,record in zip(selected,records):
            result=record['result'];rid=result['run_id']
            run=g.db.runs.find_one(dict(run_id=rid,owner_id=g.owner_id))
            assert run and run['state']==result['state'] and run['question']==q['question']
            states[run['state']]=states.get(run['state'],0)+1
            messages=list(g.db.messages.find(dict(conversation_id=run['conversation_id'],owner_id=g.owner_id)).sort('ordinal',1))
            roles=[m['role'] for m in q['history']]+['user']
            assert len({m['ordinal'] for m in messages})==len(messages)
            assert [dict(role=m['role'],text=m['text']) for m in messages[:len(q['history'])]]==q['history']
            refs=set();assets=set()
            if run['state']=='completed':
                roles.append('assistant');assert messages[-1]['text']==run['answer']==result['answer']
                generations+=bool(run['citations'])
                events=list(g.db.run_events.find(dict(run_id=rid)).sort('seq',1))
                assert [e['type'] for e in events if e['type'] in {'run.completed','run.failed','run.cancelled','run.interrupted'}]==['run.completed']
                assert all(a['seq']<b['seq'] for a,b in zip(events,events[1:]))
                for c in run['citations']:
                    row=indexed[c['chunk_uid']];source=sources[c['document_id']]
                    assert all(c[k]==row[k] for k in ('document_id','revision_id','text'))
                    assert all(c[k]==row['metadata'][k] for k in ('asset_ids','source_refs'))
                    assert c['revision_id']==source['revision_id']
                    refs.update((source['original_sha256'],r['page'],None) for r in c['source_refs'] if r.get('page'))
                    assets.update(c['asset_ids'])
                    for aid in c['asset_ids']:
                        a=g.db.knowledge_assets.find_one(dict(asset_id=aid,document_id=c['document_id'],revision_id=c['revision_id']))
                        assert a
                        if aid not in decoded_images:
                            from io import BytesIO
                            from PIL import Image
                            data=g.originals.get(a['object_key'],a['sha256'])
                            with Image.open(BytesIO(data)) as image:image.verify()
                            with Image.open(BytesIO(data)) as image:
                                image.load();assert image.width>0 and image.height>0
                            decoded_images.add(aid)
                        refs.update((source['original_sha256'],r['page'],a['sha256']) for r in a['source_refs'] if r.get('page'))
                assert set(re.findall(r'asset://([a-zA-Z0-9_-]+)',result['answer']))<=assets
            else:assert run['state']=='awaiting_input' and result['behavior']=='clarify'
            assert [m['role'] for m in messages]==roles
            assert refs=={(r['document_sha256'],r['page'],r.get('asset_sha256')) for r in result['citations']}
            messages_count+=len(messages)
        corpus=g.verify()
    paths=[config_path,dataset,manifest]+[p for p in output.rglob('*') if p.is_file()]
    return dict(passed=True,mode='real_m4_evaluation_read_only',split=config['split'],questions=len(selected),states=states,
        persisted_messages=messages_count,logical_answer_generations=generations,new_provider_calls=0,
        corpus_sha256=corpus,image_assets_fully_decoded=len(decoded_images),human_answer_correctness=None,
        raw_evidence=[dict(path=p.as_posix(),sha256=file_sha(p)) for p in paths])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','output','report'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    # 与本轮已冻结的直连模型设置一致；只读核验不会实例化权重。
    import os
    os.environ['MODEL_HOST_URL']='';os.environ['MODEL_HOST_TOKEN']=''
    result=verify(args.config,args.output)
    with args.report.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='raw_evidence'},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # 供应商/服务异常可能含私有端点，仅保留可定位的类型与代码位置。
        import traceback
        frames=traceback.extract_tb(exc.__traceback__)
        print(json.dumps(dict(passed=False,error_type=type(exc).__name__,
            locations=[dict(file=Path(f.filename).name,line=f.lineno) for f in frames])))
        raise SystemExit(1)
