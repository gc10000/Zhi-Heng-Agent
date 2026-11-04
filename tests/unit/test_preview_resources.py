"""预览创建前拒绝已观测的宿主/daemon内存不足，不触碰旧服务。"""
import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts.operations import preview
from scripts.operations.runtime_resources import assess, collect, parse_memory


GIB = 1024 ** 3


@pytest.mark.parametrize('text,value', [('1.5GiB', 1.5 * GIB), ('512MiB', GIB / 2), ('0B', 0)])
def test_docker_memory_units(text, value):
    assert parse_memory(text) == value


@pytest.mark.parametrize('text', ['-1GiB', 'NaNMiB', '4GB junk', '', 'true', '1e9B'])
def test_invalid_memory_is_not_counted_as_zero(text):
    with pytest.raises(ValueError):
        parse_memory(text)


def test_observed_half_gib_host_and_shared_pressure_refuse_new_stack():
    result = assess(host_available=GIB // 2, daemon_total=8 * GIB,
                    container_used=6 * GIB)
    assert not result['ready']
    assert result['reasons'] == ['host_memory_low', 'daemon_headroom_low']


def test_headroom_pass_is_only_a_startup_check_not_a_capacity_claim():
    result = assess(host_available=3 * GIB, daemon_total=8 * GIB,
                    container_used=4 * GIB)
    assert result['ready'] and result['capacity_verified'] is False


@pytest.mark.parametrize('values', [dict(host_available=None, daemon_total=8 * GIB, container_used=0),
                                   dict(host_available=True, daemon_total=8 * GIB, container_used=0),
                                   dict(host_available=4 * GIB, daemon_total=8 * GIB, container_used=9 * GIB)])
def test_unknown_or_inconsistent_measurement_refuses(values):
    assert assess(**values)['ready'] is False


def test_collect_queries_only_readonly_daemon_ports_and_counts_all_containers():
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs['timeout'] <= 15
        assert not any(x in command for x in ['run', 'exec', 'stop', 'update', 'prune'])
        if command[1] == 'info':
            return SimpleNamespace(returncode=0, stdout=str(8 * GIB), stderr='')
        return SimpleNamespace(returncode=0, stdout='1.5GiB / 8GiB\n512MiB / 8GiB\n', stderr='')

    result = collect(run=run, available=lambda: 4 * GIB)
    assert result['ready']
    assert result['container_used_bytes'] == 2 * GIB
    assert len(calls) == 2


def test_daemon_failure_is_unknown_and_does_not_publish_stderr():
    def run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout='', stderr='private-config-must-not-escape')

    result = collect(run=run, available=lambda: 4 * GIB)
    assert not result['ready'] and 'docker_unavailable' in result['reasons']
    assert 'private-config' not in json.dumps(result)


def test_daemon_timeout_does_not_retry_or_publish_command_output():
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        raise subprocess.TimeoutExpired(command, 12, output='private-value')

    result = collect(run=run, available=lambda: 4 * GIB)
    assert not result['ready'] and 'docker_timeout' in result['reasons']
    assert len(calls) == 1 and 'private-value' not in json.dumps(result)


def test_empty_stats_is_zero_only_if_running_container_list_is_also_empty():
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=str(8 * GIB) if command[1] == 'info' else '', stderr='')

    result = collect(run=run, available=lambda: 4 * GIB)
    assert result['ready'] and result['container_used_bytes'] == 0
    assert calls[-1] == ['docker', 'ps', '-q']


def test_empty_stats_with_a_running_container_is_unknown():
    def run(command, **kwargs):
        text = str(8 * GIB) if command[1] == 'info' else ('a-container' if command[1] == 'ps' else '')
        return SimpleNamespace(returncode=0, stdout=text, stderr='')

    result = collect(run=run, available=lambda: 4 * GIB)
    assert not result['ready'] and result['container_used_bytes'] is None


def test_create_refuses_before_configuration_directory_or_compose(monkeypatch, tmp_path):
    import scripts.operations.runtime_resources as resources
    monkeypatch.setattr(resources, 'collect', lambda: {'ready': False, 'reasons': ['host_memory_low']})
    monkeypatch.setattr(preview.sys, 'argv', ['preview.py', 'create', '--output', str(tmp_path / 'not-created')])
    monkeypatch.setattr(preview, 'compose', lambda *args: pytest.fail('must not start compose'))
    with pytest.raises(SystemExit) as e:
        preview.main()
    assert e.value.code != 0
    assert not (tmp_path / 'not-created').exists()


def test_resources_dropping_after_build_preserve_configuration_but_do_not_start(monkeypatch, tmp_path):
    import scripts.operations.runtime_resources as resources
    import scripts.operations.prepare_preview as preparation
    values = iter([{'ready': True}, {'ready': False, 'reasons': ['host_memory_low']}])
    monkeypatch.setattr(resources, 'collect', lambda: next(values))
    calls = []
    monkeypatch.setattr(preview, 'compose', lambda *args: calls.append(args))
    monkeypatch.setattr(preview, 'ensure_minio', lambda *args: None)
    config = tmp_path / 'new-runtime.env'

    def prepare(path):
        config.write_text('synthetic', encoding='utf-8')
        return {'env_file': str(config)}

    monkeypatch.setattr(preparation, 'prepare', prepare)
    monkeypatch.setattr(preview.sys, 'argv', ['preview.py', 'create', '--output', str(tmp_path / 'new')])
    with pytest.raises(SystemExit):
        preview.main()
    assert config.exists()
    assert all('up' not in call and 'exec' not in call for call in calls)
