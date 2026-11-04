"""只读预览启动检查；拒绝低内存/未知测量，不清理、调参或启动任何容器。"""
import argparse
import ctypes
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess


GIB = 1024 ** 3
MIN_HOST_AVAILABLE = 2 * GIB
MIN_DAEMON_HEADROOM = 3 * GIB


def parse_memory(text):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|TiB|kB|KB|MB|GB|TB)', text.strip())
    if not match:
        raise ValueError('Docker内存采样格式无效')
    units = dict(B=1, KiB=1024, MiB=1024**2, GiB=GIB, TiB=1024**4,
                 kB=1000, KB=1000, MB=1000**2, GB=1000**3, TB=1000**4)
    return int(Decimal(match[1]) * units[match[2]])


def host_available():
    if os.name == 'nt':
        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in (
                    'total_physical', 'available_physical', 'total_pagefile', 'available_pagefile',
                    'total_virtual', 'available_virtual', 'available_extended')]
        value = MemoryStatus()
        value.length = ctypes.sizeof(value)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            raise OSError('无法读取宿主内存')
        return value.available_physical
    text = Path('/proc/meminfo').read_text('ascii')
    match = re.search(r'^MemAvailable:\s+(\d+)\s+kB$', text, re.M)
    if not match:
        raise ValueError('缺少宿主MemAvailable')
    return int(match[1]) * 1024


def assess(*, host_available, daemon_total, container_used):
    result = dict(ready=False, reasons=[], host_available_bytes=host_available,
                  daemon_total_bytes=daemon_total, container_used_bytes=container_used,
                  estimated_daemon_headroom_bytes=None,
                  minimum_host_available_bytes=MIN_HOST_AVAILABLE,
                  minimum_daemon_headroom_bytes=MIN_DAEMON_HEADROOM, capacity_verified=False)
    values = (host_available, daemon_total, container_used)
    if (any(type(x) is not int or x < 0 for x in values)
            or daemon_total == 0 or container_used > daemon_total):
        result['reasons'].append('memory_measurement_unknown_or_inconsistent')
        return result
    headroom = daemon_total - container_used
    result['estimated_daemon_headroom_bytes'] = headroom
    if host_available < MIN_HOST_AVAILABLE:
        result['reasons'].append('host_memory_low')
    if headroom < MIN_DAEMON_HEADROOM:
        result['reasons'].append('daemon_headroom_low')
    result['ready'] = not result['reasons']
    return result


def collect(*, run=subprocess.run, available=host_available):
    host = total = used = None
    error = None
    try:
        host = available()
        info = run(['docker', 'info', '--format', '{{json .MemTotal}}'],
                   capture_output=True, text=True, timeout=12)
        if info.returncode:
            raise OSError('docker_unavailable')
        total = json.loads(info.stdout)
        stats = run(['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}}'],
                    capture_output=True, text=True, timeout=12)
        if stats.returncode:
            raise OSError('docker_unavailable')
        lines = stats.stdout.strip().splitlines()
        # 空输出可能是无容器；stats成功后只读ps核实，不能把采样缺失当0。
        if not lines:
            ps = run(['docker', 'ps', '-q'], capture_output=True, text=True, timeout=12)
            if ps.returncode or ps.stdout.strip():
                raise ValueError('stats_missing')
        values = [line.split('/') for line in lines]
        if any(len(parts) != 2 for parts in values):
            raise ValueError('stats_invalid')
        used = sum(parse_memory(parts[0]) for parts in values)
        if any(parse_memory(parts[1]) <= 0 for parts in values):
            raise ValueError('stats_invalid')
    except subprocess.TimeoutExpired:
        error = 'docker_timeout'
    except (OSError, ValueError, TypeError):
        error = 'docker_unavailable' if total is None and host is not None else 'memory_measurement_unavailable'
    result = assess(host_available=host, daemon_total=total, container_used=used)
    if error:
        result['ready'] = False
        result['reasons'].append(error)
    result['limitations'] = ['一次只读启动快照，不证明持续稳定或模型容量',
                            'daemon余量估计未计VM/daemon及并发增长；通过后仍须观察OOM和资源']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='可选全新私有JSON，已存在则拒绝覆盖')
    args = parser.parse_args()
    result = collect()
    if args.output:
        with Path(args.output).open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['ready'] else 1)


if __name__ == '__main__':
    main()
