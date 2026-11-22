"""Check failed-job isolation and HTTP idempotency using the B17 project."""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from api_a_smoke import run as smoke


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists():raise ValueError('Use fresh evidence')
    out.mkdir(parents=True)
    url='http://127.0.0.1:18086'
    def call(path,data=None):
        req=urllib.request.Request(url+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    inp=json.loads((ROOT/'data/e13-b17-251880498/request-e11-a.json').read_text())
    failure=call('/v1/jobs',{'idempotency_key':'e13-failed-'+str(time.time_ns()),'input':dict(inp,target='0'*40)})
    for _ in range(60):
        state=call('/v1/jobs/'+failure['job_id'])
        if state['status'] in ('FAILED','TIMED_OUT','SUCCEEDED'):break
        time.sleep(1)
    assert state['status']=='FAILED',state
    (out/'failed-job.json').write_text(json.dumps(state,indent=2)+'\n')
    failed_result=call('/v1/jobs/'+failure['job_id']+'/artifacts')
    (out/'failed-result.json').write_text(json.dumps(failed_result,indent=2)+'\n')
    smoke(url,ROOT/'data/e13-b17-251880498/request-e11-a.json',out/'success',180)
    summary=json.loads((out/'success/summary.json').read_text())
    assert summary['job_id']!=state['job_id'] and summary['trace_id']!=state['trace_id']
    assert call('/v1/jobs/'+state['job_id'])['status']=='FAILED'
    value={'C7':True,'C8':True,'failure':state,'success':summary,'scope':'actual HTTP B17 A-side detection; separate jobs and downloaded checksummed evidence'}
    (out/'summary.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
