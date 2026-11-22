"""Execute negative gates through the actual role HTTP boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from orchestrate import save, digest, ROOT


def http(role,payload):
    ports={'mdfixer':18084,'draft':18083,'buildchecker':18081}
    request=urllib.request.Request(f'http://127.0.0.1:{ports[role]}/v1/run',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try: response=urllib.request.urlopen(request,timeout=180)
    except urllib.error.HTTPError as exc: response=exc
    with response: return {'http':response.code,'body':json.load(response)}


def tree(root):
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--success',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    if out.exists(): raise ValueError('Use fresh evidence')
    out.mkdir(parents=True)
    results=[]
    successful=args.success.resolve()
    result=json.loads((successful/'result.json').read_text())
    report_path=successful/'incremental/incremental-check.json'
    original=json.loads(report_path.read_text())
    request=json.loads((successful/'request.json').read_text())
    project=out/'source'
    subprocess.run(['git','clone','--no-hardlinks',request['repo'],str(project)],check=True,capture_output=True)
    subprocess.run(['git','checkout','--detach',request['target']],cwd=project,check=True,capture_output=True)
    initial=tree(project)
    def payload(report,folder):
        return {'project':str(project),'out':str(folder),'report':str(report),'report_sha256':digest(report),
                'target_commit':request['target'],'job_id':result['job_id'],'trace_id':result['trace_id'],
                'expected_output':request['expected_output'],'header_change_output':request.get('header_change_output','2')}
    def record(case,passed,**data):
        results.append({'case':case,'passed':bool(passed),**data})
        save(out/'summary.json',results)
    # C2: preserve matching checksum but deliberately change the commit.
    stale=out/'stale.json';save(stale,dict(original,commit=request['base']))
    response=http('mdfixer',payload(stale,out/'stale-repair'))
    record('C2',response['http']==422 and 'identity mismatch' in response['body'].get('error','') and tree(project)==initial,response=response)
    # C3: bytes change after the sender computed the checksum.
    changed=out/'changed.json';shutil.copyfile(report_path,changed)
    transfer=payload(changed,out/'changed-repair')
    changed.write_bytes(changed.read_bytes()+b' ')
    response=http('mdfixer',transfer)
    record('C3',response['http']==422 and 'hash mismatch' in response['body'].get('error','') and tree(project)==initial,response=response)
    # C5: a syntactically valid but ineffective repair must be rejected.
    bad=dict(original,data=dict(original['data'],findings=[{'type':'MISSING','target':'helper.o','dependency':'config.h'}]))
    bad_path=out/'bad-report.json';save(bad_path,bad)
    response=http('mdfixer',payload(bad_path,out/'rejected-repair'))
    validation=json.loads((out/'rejected-repair/validation/validation.json').read_text())
    record('C5',response['http']==422 and not validation['accepted'] and validation['rollback'] and tree(project)==initial,response=response,validation=validation,before=initial,after=tree(project))
    # C6: fake key lives only in an isolated probe, and is removed afterwards.
    probe=out/'fake-key-probe';probe.mkdir()
    marker=probe/'runtime.log'
    marker.write_text('api_key = "'+'sk-'+'demo1234567890abcdefghijk'+'"\n')
    before=digest(marker)
    scan=[sys.executable,str(ROOT/'labs/e13e14/scan_runtime_logs.py'),str(probe)]
    blocked=subprocess.run(scan,text=True,capture_output=True)
    marker.write_text('api_key = "<removed>"\n')
    clean=subprocess.run(scan,text=True,capture_output=True)
    record('C6',blocked.returncode==1 and clean.returncode==0,before_sha256=before,after_sha256=digest(marker),blocked_exit=blocked.returncode,clean_exit=clean.returncode,masked_output=blocked.stdout,clean_output=clean.stdout)
    response=http('buildchecker',[])
    record('JSON_OBJECT',response['http']==422,response=response)
    # Verify every saved manifest in the successful run, including stage identity.
    checked=0
    for ref in result['artifacts']:
        p=successful/ref['uri'];assert digest(p)==ref['sha256'];assert p.stat().st_size==ref['bytes'];checked+=1
    stages=[]
    for ref in result['stages']:
        p=successful/ref['artifact']['uri']; assert digest(p)==ref['artifact']['sha256']
        stage=json.loads(p.read_text()); assert stage['job_id']==result['job_id'] and stage['trace_id']==result['trace_id']
        assert stage['commit']==(request['base'] if stage['name']=='full-check' else request['target'])
        stages.append(stage['name'])
    used=json.loads((successful/'repair-response.json').read_text())
    record('C1_LOCAL_FOUR_ROLES',result['status']=='SUCCEEDED' and used['validation']['accepted'] and stages==['draft','full-check','incremental-check','repair','recheck'],job_id=result['job_id'],trace_id=result['trace_id'],report_sha256=digest(report_path),verified_artifacts=checked,stages=stages,scope='B17 project executed on A17 four role services; counterpart independent acceptance remains separate')
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return 0 if all(x['passed'] for x in results) else 1


if __name__=='__main__':
    import sys
    raise SystemExit(main())
