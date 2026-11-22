"""Observe runtime container cleanup after a real verification timeout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'labs/e11e12/vendor')]
from draft.autobuild import auto_build


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists():raise ValueError('Use fresh evidence')
    out.mkdir(parents=True)
    source=ROOT/'data/integration-sample/repo'
    fixture=out/'fixture';shutil.copytree(source,fixture,ignore=shutil.ignore_patterns('.git','*.o','app'))
    command='CMD ["python3", "-c", "import subprocess,time; subprocess.Popen([\'sleep\',\'120\']); time.sleep(120)"]'
    broken=fixture/'Dockerfile.broken'
    broken.write_text(broken.read_text().replace('CMD ["./app"]',command))
    candidate=out/'candidate.Dockerfile'
    original=ROOT/'data/integration-sample/candidate-A17-local.Dockerfile'
    if not original.exists():original=ROOT/'data/integration-sample/candidate.Dockerfile'
    candidate.write_text(original.read_text().replace('CMD ["./app"]',command))
    before=subprocess.check_output(['docker','ps','-q','--no-trunc'],text=True).splitlines()
    result=auto_build(fixture,candidate,out/'runtime','unused',timeout=300,verify_timeout=0.25)
    cid=(out/'runtime/verify-container-id.txt').read_text().strip()
    inspect=subprocess.run(['docker','inspect',cid],capture_output=True,text=True)
    after=subprocess.check_output(['docker','ps','-q','--no-trunc'],text=True).splitlines()
    # The sleep process and its child share the container removed by auto_build.
    summary={'status':result['status'],'container_id':cid,'container_inspect_exit':inspect.returncode,
             'no_new_running_container':not(set(after)-set(before)),
             'before_running_containers':before,'after_running_containers':after,
             'cleanup_log':(out/'runtime/cleanup.log').read_text(),
             'passed':result['status']=='TIMED_OUT' and inspect.returncode!=0 and not(set(after)-set(before))}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0 if summary['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
