"""Offline A-track evidence verification; does not run Docker/GCC/strace."""
import argparse
import hashlib
import json
from pathlib import Path
import re

TARGETS = ('main.o', 'helper.o')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def findings(items):
    return sorted((x['type'], x['target'], x['dependency'])
                  for x in items if x['target'] in TARGETS)


def verify(folder):
    folder = Path(folder).resolve()
    result = read(folder / 'result.json')
    require(result['status'] == 'SUCCEEDED', 'Result did not succeed')
    require(result['schema_version'] == 'e11e12-1', 'Result schema mismatch')
    jid, tid = result['job_id'], result['trace_id']
    base, target = result['base_commit'], result['target_commit']
    require(all(re.fullmatch(r'[0-9a-f]{40}', sha) for sha in (base, target)),
            'Expected full SHA-1 commit IDs for this profile')
    checked = set()

    def check_artifact(ref):
        prefix = f'artifact://{jid}/'
        require(ref['uri'].startswith(prefix), 'Artifact job_id mismatch')
        path = (folder / ref['uri'][len(prefix):]).resolve()
        require(path.is_relative_to(folder) and path.is_file(),
                'Artifact missing or outside evidence directory')
        content = path.read_bytes()
        require(hashlib.sha256(content).hexdigest() == ref['sha256'],
                f'Artifact hash mismatch: {path.name}')
        require(len(content) == ref['bytes'], f'Artifact size mismatch: {path.name}')
        checked.add(path.relative_to(folder).as_posix())
        return path

    stages = {stage['name']: stage for stage in result['stages']}
    for name, commit in [('full-check', base), ('incremental-check', target)]:
        require(name in stages, f'Missing stage: {name}')
        envelope = read(check_artifact(stages[name]['artifact']))
        require(envelope['schema_version'] == 'e11e12-1', f'{name}: schema mismatch')
        require(envelope['kind'] == name, f'{name}: kind mismatch')
        require(envelope['status'] == 'SUCCEEDED', f'{name}: stage failed')
        require(envelope['job_id'] == jid and envelope['trace_id'] == tid,
                f'{name}: job_id/trace_id mismatch')
        require(envelope['commit'] == commit, f'{name}: stale commit')
        for ref in envelope['artifacts']:
            check_artifact(ref)
    for ref in result['artifacts']:
        check_artifact(ref)

    cache = read(folder / 'baseline-cache.json')
    increment = read(folder / 'incremental-report.json')
    full_report = read(folder / 'target-full/findings.json')
    edges = read(folder / 'baseline-full/actual-graph.json')
    projected = {t: sorted({edge['dependency'] for edge in edges if edge['target'] == t})
                 for t in TARGETS}
    require(cache['commit'] == base and increment['commit'] == target,
            'Cache/report commit mismatch')
    require(cache['actual'] == projected, 'Baseline cache does not match BuildChecker graph')
    require(full_report['status'] == 'SUCCEEDED', 'Target full check did not succeed')
    require(findings(increment['findings']) == findings(full_report['findings']),
            'Incremental/full findings differ')
    envelope = read(folder / 'incremental-check.json')
    require(envelope['data'] == increment, 'Incremental envelope differs from raw report')
    previous = set(findings(cache['findings']))
    current = set(findings(increment['findings']))
    require(sorted(map(tuple, increment['added'])) == sorted(current - previous),
            'Incorrect added findings')
    require(sorted(map(tuple, increment['resolved'])) == sorted(previous - current),
            'Incorrect resolved findings')
    return {'verification': 'PASSED', 'method': 'offline saved-evidence verification',
            'job_id': jid, 'trace_id': tid, 'base_commit': base, 'target_commit': target,
            'verified_artifact_count': len(checked),
            'baseline_graph_matches_cache': True, 'incremental_matches_full': True,
            'findings': increment['findings'], 'added': increment['added'],
            'refreshed': increment['refreshed'], 'reused': increment['reused']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    summary = verify(args.folder)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
