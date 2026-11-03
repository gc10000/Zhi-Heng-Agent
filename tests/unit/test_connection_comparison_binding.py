import json

from copy import deepcopy

import pytest

from app.answering.comparison_answers import bind_comparison_response, validate_saved_comparison
from app.knowledge.repository import fingerprint


def catalog():
    def item(ref, pid, text, frame=0, kind='source_document', page=4, uid=None):
        return dict(reference_number=ref, frame_index=frame, document_id='d-'+pid,
            revision_id='r-'+pid, chunk_uid=uid or 'c-'+pid+str(frame), ordinal=ref,
            original_sha256='a'*64, source_product_ids=[pid], product_labels={pid:pid},
            physical_pages=[page], page_status='exact', source_text=text,
            scoped_text=text, heading_path=['产品概述'], source_refs=[dict(
                document_id='d-'+pid, revision_id='r-'+pid, kind='pdf', page=page)],
            frame=dict(kind=kind, scope=dict(start=0,end=len(text),text=text,sha256=fingerprint(text)),
                fields=dict.fromkeys(('origin','medium','destination','purpose'))))
    return [
        item(1, 'la', 'LA2608需要通过3G/4G网络连接到运营商无线控制器，用于管理。'),
        item(2, 'cb', 'Aolynk CB304n融合了Cable网络和无线路由器的功能。'),
        item(3, 'cb', '请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。', frame=1, kind='physical_check', page=30, uid='c-cb-path'),
    ]


def test_connection_mode_produces_qualified_answer_and_source_bound_proof():
    raw = json.dumps({'schema_version':'comparison_frame_selection_v1','frames':[]}, ensure_ascii=False)
    answer, proof = bind_comparison_response(raw, catalog(), ['la','cb'], 'device_uplink',
        'b'*64, 'c'*64, {'la':'H3C LA2608','cb':'Aolynk CB304n'},
        version='connection_comparison_v1')
    assert proof['function_version'] == 'connection_comparison_v1'
    assert proof['comparison_status'] == 'qualified_medium_difference'
    assert '3G/4G' in answer and '同轴' in answer
    assert '现场链路已经建立' in answer
    assert proof['source_facts'] and proof['result']['support_fact_ids']


def test_connection_mode_rejects_tampered_saved_proof():
    raw = json.dumps({'schema_version':'comparison_frame_selection_v1','frames':[]}, ensure_ascii=False)
    answer, proof = bind_comparison_response(raw, catalog(), ['la','cb'], 'device_uplink',
        'b'*64, 'c'*64, {'la':'LA','cb':'CB'}, version='connection_comparison_v1')
    proof['result']['status'] = 'qualified_medium_same'
    assert answer != '两份资料记载的连接介质相同；这只适用于下列同层来源事实。'


def test_connection_mode_rebinds_assembly_and_rejects_source_or_manifest_rewrite():
    raw = json.dumps({'schema_version':'comparison_frame_selection_v1','frames':[]}, ensure_ascii=False)
    context = dict(function_version='comparison_source_assembly_v1',
        status='complete', documents=['c-la0', 'c-cb0', 'c-cb-path'],
        dependencies=[], dropped=[], issues=[])
    context['identity_sha256'] = fingerprint(context)
    answer, proof = bind_comparison_response(raw, catalog(), ['la','cb'], 'device_uplink',
        'b'*64, 'c'*64, {'la':'LA','cb':'CB'}, version='connection_comparison_v1',
        comparison_context=context)
    row = dict(answer=answer, comparison_answer=proof,comparison_context_assembly=context)
    validate_saved_comparison(row, catalog(), ['la','cb'], 'device_uplink',
        'b'*64, 'c'*64, {'la':'LA','cb':'CB'}, version='connection_comparison_v1')

    changed = deepcopy(row)
    changed['comparison_answer']['comparison_context']['documents'] = ['c-la0']
    with pytest.raises(ValueError):
        validate_saved_comparison(changed, catalog(), ['la','cb'], 'device_uplink',
            'b'*64, 'c'*64, {'la':'LA','cb':'CB'}, version='connection_comparison_v1')

    changed = deepcopy(row)
    changed['comparison_answer']['source_facts'][0]['medium'] = 'tampered'
    with pytest.raises(ValueError):
        validate_saved_comparison(changed, catalog(), ['la','cb'], 'device_uplink',
            'b'*64, 'c'*64, {'la':'LA','cb':'CB'}, version='connection_comparison_v1')
