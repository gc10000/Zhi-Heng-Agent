"""任务阶段及向量批次持久检查点，每次保存都复核当前attempt/token。"""
import json
from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint


class Checkpoints:
    def __init__(self, jobs, row, originals):
        self.jobs, self.row, self.originals = jobs, row, originals

    def fence(self):
        return self.jobs.fence(self.row['job_id'], self.row['attempt'], self.row['lease_token'])

    def save(self, stage, manifest):
        self.jobs.save(self.row['job_id'], self.row['attempt'], self.row['lease_token'],
                       {'stage': stage, 'checkpoints.' + stage: manifest})


class CheckpointEmbedder:
    def __init__(self, checkpoints, encode, *, identity, batch_size=32):
        self.checkpoints, self.encode, self.identity, self.batch_size = checkpoints, encode, identity, batch_size

    def __call__(self, texts):
        dense, sparse = [], []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start+self.batch_size]
            key = fingerprint([self.identity, start, batch])
            row = self.checkpoints.fence()
            saved = row.get('checkpoints', {}).get('embeddings', {}).get(key)
            if saved:
                result = json.loads(self.checkpoints.originals.get(saved['object_key'], saved['sha256']))
            else:
                self.checkpoints.save('embedding_pending', {'batch_hash': key, 'start': start, 'count': len(batch)})
                result = self.encode(batch)
                data = json.dumps(result, sort_keys=True).encode()
                digest = content_hash(data)
                object_key = self.checkpoints.originals.prefix + 'embeddings/' + self.checkpoints.row['revision_id'] + '/' + key
                self.checkpoints.fence()
                self.checkpoints.originals.put(object_key, data, 'application/json')
                self.checkpoints.jobs.save(row['job_id'], row['attempt'], row['lease_token'],
                    {'stage': 'embedding', 'checkpoints.embeddings.' + key: {'object_key': object_key, 'sha256': digest}})
            dense.extend(result['dense'])
            sparse.extend({int(k): float(v) for k, v in vector.items()} for vector in result['sparse'])
        return {'dense': dense, 'sparse': sparse}
