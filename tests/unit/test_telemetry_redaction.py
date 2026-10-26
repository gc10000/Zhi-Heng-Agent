from types import SimpleNamespace
from app.runs.telemetry import run_telemetry


class Cursor:
    def __init__(self, rows): self.rows=rows
    def sort(self, *args): return self
    def __iter__(self): return iter(self.rows)


class Collection:
    def __init__(self, rows): self.rows=rows
    def find(self, query, projection=None): return Cursor(self.rows)


class Repo:
    def __init__(self, row, events): self.db=SimpleNamespace(run_events=Collection(events)); self.row=row
    def get(self, user, rid): return self.row


def test_telemetry_has_timing_failure_and_null_cost_without_private_fields():
    row={'run_id':'r','conversation_id':'c','state':'failed','created_at':'2026-01-01T00:00:00+00:00',
         'answer':'private answer','question':'private question','error':{'code':'upstream_timeout','stage':'answer'},
         'model_name':'private-model'}
    events=[{'seq':1,'type':'run.started','at':'2026-01-01T00:00:01+00:00','payload':{}},
            {'seq':2,'type':'stage.changed','at':'2026-01-01T00:00:02+00:00','payload':{'stage':'answer'}},
            {'seq':3,'type':'run.failed','at':'2026-01-01T00:00:04+00:00','payload':{'error':'private'}}]
    value=run_telemetry(Repo(row,events),SimpleNamespace(), 'r')
    assert value['total_seconds']==4.0 and value['stage_seconds']=={'answer':2.0}
    assert value['failure_code']=='upstream_timeout' and value['failure_stage']=='answer'
    assert value['token_usage']=={'input':None,'output':None} and value['logical_provider_calls'] is None
    assert 'answer' not in value and 'question' not in value and value['model'] == 'private-model'


def test_malformed_and_missing_times_remain_unknown():
    row={'run_id':'r','state':'running','created_at':'bad','error':{}}
    value=run_telemetry(Repo(row,[]),SimpleNamespace(),'r')
    assert value['total_seconds'] is None and value['ended_at'] is None and value['failure_stage'] is None


def test_unknown_error_stage_model_and_urls_never_escape_projection():
    row={'run_id':'r','state':'failed','error':{'code':'https://private/?token=secret', 'stage':'private prompt'},
         'model_name':'https://private/?sig=secret'}
    events=[{'seq':1,'type':'stage.changed','at':'2026-01-01T00:00:00Z','payload':{'stage':'private prompt'}},
            {'seq':2,'type':'run.failed','at':'2026-01-01T00:00:02Z','payload':{}}]
    value=run_telemetry(Repo(row,events),SimpleNamespace(),'r')
    assert 'secret' not in str(value) and 'private prompt' not in str(value)
    assert value['failure_code']=='unknown' and value['model'] is None


def test_repeated_stage_events_accumulate_and_missing_revision_is_unknown():
    row={'run_id':'r','state':'completed','created_at':'2026-01-01T00:00:00Z'}
    events=[{'seq':n+1,'type':kind,'at':f'2026-01-01T00:00:0{n}Z','payload':{'stage':'retrieve'}}
            for n,kind in enumerate(['run.started','stage.changed','stage.changed','run.completed'])]
    value=run_telemetry(Repo(row,events),SimpleNamespace(),'r')
    assert value['stage_seconds']=={'retrieve':2.0}
    assert value['revision_count'] is None
