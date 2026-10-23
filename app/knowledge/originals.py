"""原件和解析产物按稳定身份存储；读取先校验前缀与hash。"""
from io import BytesIO
from app.knowledge.models import content_hash,stable_id


class OriginalStore:
    def __init__(self,client,*,bucket,prefix):
        if not prefix or prefix.startswith('/') or '..' in prefix:raise ValueError('原件对象前缀非法')
        self.client,self.bucket,self.prefix=client,bucket,prefix.rstrip('/')+'/'

    def key(self,document_id,digest):return self.prefix+'originals/'+stable_id('original',document_id,[digest])

    def put(self,key,data,media_type='application/octet-stream'):
        if not key.startswith(self.prefix):raise ValueError('对象不在当前存储前缀')
        self.client.put_object(self.bucket,key,BytesIO(data),len(data),content_type=media_type)

    def get(self,key,digest):
        if not key.startswith(self.prefix):raise ValueError('对象不在当前存储前缀')
        response=self.client.get_object(self.bucket,key)
        try:data=response.read()
        finally:response.close();response.release_conn()
        if content_hash(data)!=digest:raise ValueError('对象hash不符')
        return data

    def read(self,revision):return self.get(revision['object_key'],revision['original_sha256'])

    def put_parsed(self,revision_id,data):
        digest=content_hash(data);key=self.prefix+'parsed/'+stable_id('parsed',revision_id,[digest])
        self.put(key,data,'application/json')
        return {'object_key':key,'sha256':digest}

    def put_image_source(self,revision_id,image_id,data):
        digest=content_hash(data);key=self.prefix+'source-images/'+stable_id('image-original',revision_id,[image_id,digest])
        self.put(key,data)
        return {'object_key':key,'sha256':digest}
