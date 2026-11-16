"""A-side HTTP smoke test and artifact download against an existing course API."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from verify_a import verify


def run(url, request_file, out, timeout):
    if out.exists():
        raise ValueError('OUTPUT_EXISTS: choose a fresh client output directory')
    out.mkdir(parents=True)
    records = []

    def request(path, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        req = Request(url.rstrip('/') + path, data=payload,
                      headers={'Content-Type': 'application/json'} if payload else {})
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            content = response.read()
            headers = dict(response.headers)
            code = response.code
        record = {'path': path, 'method': 'POST' if payload else 'GET', 'status': code}
        if headers.get('Content-Type', '').startswith('application/json'):
            record['response'] = json.loads(content)
        else:
            record.update(sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
        records.append(record)
        (out / 'transcript.json').write_text(json.dumps(records, indent=2) + '\n')
        return code, headers, content

    assert request('/health')[0] == 200
    inp = json.loads(request_file.read_text())
    if inp['mode'] != 'e11-a':
        raise ValueError('This client deliberately submits only e11-a')
    body = {'idempotency_key': 'A17-241880606-' + str(time.time_ns()), 'input': inp}
    (out / 'submission.json').write_text(json.dumps(body, indent=2) + '\n')
    code, _, data = request('/v1/jobs', body)
    assert code == 202
    job = json.loads(data)
    code, _, data = request('/v1/jobs', body)
    assert code == 202 and json.loads(data)['job_id'] == job['job_id']
    changed = dict(body, input=dict(inp, target='0' * 40))
    code, _, data = request('/v1/jobs', changed)
    assert code == 409 and json.loads(data)['error'] == 'IDEMPOTENCY_CONFLICT'
    invalid = {'idempotency_key': body['idempotency_key'] + '-invalid',
               'input': dict(inp, mode='invalid')}
    assert request('/v1/jobs', invalid)[0] == 400
    prefix = '/v1/jobs/' + job['job_id']
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code, _, data = request(prefix)
        assert code == 200
        state = json.loads(data)
        if state['status'] in ('SUCCEEDED', 'FAILED', 'TIMED_OUT'):
            break
        time.sleep(1)
    else:
        raise TimeoutError('Client wait expired; server job may still be running')
    assert state['status'] == 'SUCCEEDED', state
    code, _, data = request(prefix + '/artifacts')
    assert code == 200
    result = json.loads(data)
    evidence = out / 'downloaded-evidence'
    evidence.mkdir()
    (evidence / 'result.json').write_bytes(data)
    for ref in result['artifacts']:
        scheme = 'artifact://' + job['job_id'] + '/'
        assert ref['uri'].startswith(scheme)
        relative = ref['uri'][len(scheme):]
        dest = (evidence / relative).resolve()
        assert dest.is_relative_to(evidence.resolve())
        code, headers, content = request(prefix + '/files/' + quote(relative, safe='/'))
        assert code == 200
        digest = hashlib.sha256(content).hexdigest()
        assert digest == ref['sha256'] == headers['X-Content-SHA256']
        assert len(content) == ref['bytes']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    assert request(prefix + '/files/%2e%2e/%2e%2e/state.json')[0] == 404
    verification = verify(evidence)
    summary = {'passed': True, 'job_id': state['job_id'], 'trace_id': state['trace_id'],
               'same_key_same_job': True, 'changed_input_returns_409': True,
               'invalid_mode_returns_400': True, 'path_escape_returns_404': True,
               'all_download_headers_match_manifest': True,
               'verification': verification}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:18086')
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    run(args.url, args.request, args.out.resolve(), args.timeout)
