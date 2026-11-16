"""Run real GCC/Git A-track cases inside the Linux course image."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'labs/e8e10'))
sys.path.insert(0, str(ROOT / 'labs/e11e12'))
from lab import fixture, commit, scan, save
from pipeline import check_envelope, Failure


def main(out):
    if out.exists():
        raise ValueError('OUTPUT_EXISTS: choose a fresh output directory')
    out.mkdir(parents=True)
    project = out / 'project'
    fixture(project)
    baseline = scan(project)
    save(out / 'C0.json', baseline)
    # Body-only change: two object dependency observations should be reused.
    helper = project / 'helper.c'
    helper.write_text('int helper(void){return 0+0;}\n', encoding='utf-8')
    commit(project, 'A exercise: body-only change')
    body = scan(project, baseline)
    assert body['refreshed'] == [] and sorted(body['reused']) == ['helper.o', 'main.o']
    save(out / 'C1-body.json', body)
    # A preprocessor change invalidates the global key, refreshing both targets.
    main = project / 'main.c'
    main.write_text('#include "extra.h"\n' + main.read_text(encoding='utf-8'), encoding='utf-8')
    commit(project, 'A exercise: add extra.h include')
    include = scan(project, body)
    assert sorted(include['refreshed']) == ['helper.o', 'main.o'] and include['reused'] == []
    assert ['MISSING', 'main.o', 'extra.h'] in include['added']
    full = scan(project)
    assert all(include[key] == full[key] for key in ('actual', 'declared', 'findings'))
    save(out / 'C2-include.json', include)
    save(out / 'C2-full-gcc.json', full)
    envelope = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
                'status': 'SUCCEEDED', 'commit': body['commit'], 'data': body}
    try:
        check_envelope(envelope, include['commit'], 'incremental-check')
    except Failure as error:
        assert error.code == 'STALE_REPORT'
        save(out / 'stale-report.json', {'error': error.code,
             'report_commit': body['commit'], 'target_commit': include['commit']})
    else:
        raise AssertionError('Expected STALE_REPORT')
    summary = {'passed': True, 'source': 'course-generated exercise commits',
               'body_commit': body['commit'], 'include_commit': include['commit'],
               'body_reused': body['reused'], 'include_refreshed': include['refreshed'],
               'gcc_incremental_matches_fresh_scan': True, 'stale_report_rejected': True,
               'scope': 'GCC cache cases only; use E11-A run for strace full-check comparison'}
    save(out / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out.resolve())
