"""按实际证据同步 M0 任务记录；不自动判定测试通过。"""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def record(task, detail, next_action, complete):
    records = ROOT / 'docs/development/records'
    path = records / f'{task}.md'
    if path.exists():
        with path.open('a', encoding='utf-8') as handle:
            handle.write('\n\n' + detail)
    else:
        path.write_text(f'# {task} · 2026-10-22\n\n' + detail, encoding='utf-8')
    if complete:
        p = ROOT / 'docs/plans/DEVELOPMENT_TODO.md'
        p.write_text(p.read_text(encoding='utf-8').replace(f'- [ ] **{task}**', f'- [x] **{task}**'), encoding='utf-8')
        p = ROOT / 'docs/plans/tasks/M0-baseline.md'
        p.write_text(re.sub(r'- \[ \] (\*\*' + task + r'\.)', r'- [x] \1', p.read_text(encoding='utf-8')), encoding='utf-8')
    done = len(re.findall(r'- \[x\] \*\*M0-\d+\*\*', (ROOT / 'docs/plans/DEVELOPMENT_TODO.md').read_text(encoding='utf-8')))
    p = ROOT / 'docs/development/PROGRESS.md'
    p.write_text(f'''# 开发进度与接续点

更新日期：2026-10-22。

**当前状态：**M0 按已批准计划顺序执行；M1 未授权。
**当前任务：**{task}（{'已验收' if complete else '进行中'}）。
**下一动作：**{next_action}
**阶段统计：**M0 {done}/9；核心 {done}/76；可选 0/2；其他阶段 0。

## 本次记录

{detail}

## 固定边界

无 Git，不初始化、不推送；原代码备份 evidence/originals。不接触课程原件、解析缓存、原集合数据和桶策略。单元 fake 与真实集成分开记录。总控审查未通过，不进入 M1。

各任务完整命令/失败历史/数据范围/回滚见 records/M0-*.md；环境见 baseline.md 和 evidence/M0-01-environment.json。
''', encoding='utf-8')
    p = ROOT / 'docs/development/CHANGELOG.md'
    with p.open('a', encoding='utf-8') as handle:
        handle.write(f'\n\n## 2026-10-22 · {task} · {"已验收" if complete else "进行中"}\n\n{detail}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task')
    parser.add_argument('--detail-file', type=Path, required=True)
    parser.add_argument('--next', required=True)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    record(args.task, args.detail_file.read_text(encoding='utf-8'), args.next, args.complete)
